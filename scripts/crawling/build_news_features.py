import argparse
import os
from datetime import timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_SCHEMA_STAGING = os.getenv("DB_SCHEMA", "staging")
DB_SCHEMA_DWH = os.getenv("DB_SCHEMA_DWH", "dwh")


NEWS_METRIC_MAP = {
    "sentiment_score_t1": "news_sent_score_t1",
    "sentiment_score_t3": "news_sent_score_t3",
    "sentiment_score_t7": "news_sent_score_t7",
    "good_cnt_t1": "news_good_cnt_t1",
    "good_cnt_t3": "news_good_cnt_t3",
    "good_cnt_t7": "news_good_cnt_t7",
    "bad_cnt_t1": "news_bad_cnt_t1",
    "bad_cnt_t3": "news_bad_cnt_t3",
    "bad_cnt_t7": "news_bad_cnt_t7",
    "coverage_t1": "news_coverage_t1",
    "coverage_t3": "news_coverage_t3",
    "coverage_t7": "news_coverage_t7",
}

MARKET_METRIC_MAP = {
    "sentiment_score_t1": "mkt_news_sent_score_t1",
    "sentiment_score_t3": "mkt_news_sent_score_t3",
    "sentiment_score_t7": "mkt_news_sent_score_t7",
}


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        pool_pre_ping=True,
    )


def load_trade_dates(engine, days_back):
    query = text(
        f"""
        SELECT DISTINCT period_date::date AS period_date
        FROM {DB_SCHEMA_DWH}.fact_metric
        WHERE period_type = 'daily'
          AND metric_code = 'close_price'
          AND period_date >= current_date - CAST(:days_back AS int) * INTERVAL '1 day'
        ORDER BY period_date
        """
    )
    return pd.read_sql(query, engine, params={"days_back": days_back})


def load_active_symbols(engine):
    query = text(
        f"""
        SELECT symbol_key, symbol_code
        FROM {DB_SCHEMA_STAGING}.dim_symbol
        WHERE is_active = TRUE
        ORDER BY symbol_key
        """
    )
    return pd.read_sql(query, engine)


def load_symbol_news_daily(engine, min_date):
    query = text(
        f"""
        SELECT
            ds.symbol_key,
            date(na.published_at) AS period_date,
            AVG(na.sentiment_score) AS sentiment_score,
            SUM(CASE WHEN na.sentiment_label = 'good' THEN 1 ELSE 0 END) AS good_cnt,
            SUM(CASE WHEN na.sentiment_label = 'bad' THEN 1 ELSE 0 END) AS bad_cnt,
            COUNT(*) AS coverage
        FROM {DB_SCHEMA_STAGING}.fact_news_article na
        JOIN {DB_SCHEMA_STAGING}.bridge_news_symbol bns
          ON na.article_id = bns.article_id
        JOIN {DB_SCHEMA_STAGING}.dim_symbol ds
          ON bns.symbol_code = ds.symbol_code
        WHERE na.published_at IS NOT NULL
          AND date(na.published_at) >= :min_date
        GROUP BY ds.symbol_key, date(na.published_at)
        """
    )
    return pd.read_sql(query, engine, params={"min_date": min_date})


def load_market_news_daily(engine, min_date):
    query = text(
        f"""
        SELECT
            date(published_at) AS period_date,
            AVG(sentiment_score) AS sentiment_score,
            SUM(CASE WHEN sentiment_label = 'good' THEN 1 ELSE 0 END) AS good_cnt,
            SUM(CASE WHEN sentiment_label = 'bad' THEN 1 ELSE 0 END) AS bad_cnt,
            COUNT(*) AS coverage
        FROM {DB_SCHEMA_STAGING}.fact_news_article
        WHERE published_at IS NOT NULL
          AND date(published_at) >= :min_date
        GROUP BY date(published_at)
        """
    )
    return pd.read_sql(query, engine, params={"min_date": min_date})


def _build_rolling_features(df_daily, date_col="period_date"):
    if df_daily.empty:
        return df_daily

    df = df_daily.sort_values(date_col).copy()
    df[date_col] = pd.to_datetime(df[date_col]).dt.date

    for window_size in (1, 3, 7):
        score_col = f"sentiment_score_t{window_size}"
        good_col = f"good_cnt_t{window_size}"
        bad_col = f"bad_cnt_t{window_size}"
        cov_col = f"coverage_t{window_size}"

        score_values = []
        good_values = []
        bad_values = []
        cov_values = []

        dates = df[date_col].tolist()
        for current_date in dates:
            start_date = current_date - timedelta(days=window_size - 1)
            mask = (df[date_col] >= start_date) & (df[date_col] <= current_date)
            window_df = df[mask]
            score_values.append(float(window_df["sentiment_score"].mean()) if not window_df.empty else 0.0)
            good_values.append(int(window_df["good_cnt"].sum()) if not window_df.empty else 0)
            bad_values.append(int(window_df["bad_cnt"].sum()) if not window_df.empty else 0)
            cov_values.append(int(window_df["coverage"].sum()) if not window_df.empty else 0)

        df[score_col] = score_values
        df[good_col] = good_values
        df[bad_col] = bad_values
        df[cov_col] = cov_values

    return df


def build_symbol_features(trade_dates, symbols, symbol_news_daily):
    if trade_dates.empty or symbols.empty:
        return pd.DataFrame()

    date_values = pd.to_datetime(trade_dates["period_date"]).dt.date.tolist()
    rows = []
    for _, sym in symbols.iterrows():
        sym_key = int(sym["symbol_key"])
        raw = symbol_news_daily[symbol_news_daily["symbol_key"] == sym_key].copy()
        raw["period_date"] = pd.to_datetime(raw["period_date"]).dt.date

        daily_map = {
            d: row
            for d, row in raw.set_index("period_date").iterrows()
        }

        base = pd.DataFrame({"period_date": date_values})
        base["sentiment_score"] = base["period_date"].map(
            lambda d: float(daily_map[d]["sentiment_score"]) if d in daily_map and pd.notna(daily_map[d]["sentiment_score"]) else 0.0
        )
        base["good_cnt"] = base["period_date"].map(
            lambda d: int(daily_map[d]["good_cnt"]) if d in daily_map and pd.notna(daily_map[d]["good_cnt"]) else 0
        )
        base["bad_cnt"] = base["period_date"].map(
            lambda d: int(daily_map[d]["bad_cnt"]) if d in daily_map and pd.notna(daily_map[d]["bad_cnt"]) else 0
        )
        base["coverage"] = base["period_date"].map(
            lambda d: int(daily_map[d]["coverage"]) if d in daily_map and pd.notna(daily_map[d]["coverage"]) else 0
        )

        feat = _build_rolling_features(base)
        feat["symbol_key"] = sym_key
        feat["period_scope"] = "symbol"
        rows.append(feat)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_market_features(trade_dates, market_news_daily):
    if trade_dates.empty:
        return pd.DataFrame()

    date_values = pd.to_datetime(trade_dates["period_date"]).dt.date.tolist()
    raw = market_news_daily.copy()
    raw["period_date"] = pd.to_datetime(raw["period_date"]).dt.date
    daily_map = {
        d: row
        for d, row in raw.set_index("period_date").iterrows()
    }

    base = pd.DataFrame({"period_date": date_values})
    base["sentiment_score"] = base["period_date"].map(
        lambda d: float(daily_map[d]["sentiment_score"]) if d in daily_map and pd.notna(daily_map[d]["sentiment_score"]) else 0.0
    )
    base["good_cnt"] = base["period_date"].map(
        lambda d: int(daily_map[d]["good_cnt"]) if d in daily_map and pd.notna(daily_map[d]["good_cnt"]) else 0
    )
    base["bad_cnt"] = base["period_date"].map(
        lambda d: int(daily_map[d]["bad_cnt"]) if d in daily_map and pd.notna(daily_map[d]["bad_cnt"]) else 0
    )
    base["coverage"] = base["period_date"].map(
        lambda d: int(daily_map[d]["coverage"]) if d in daily_map and pd.notna(daily_map[d]["coverage"]) else 0
    )

    feat = _build_rolling_features(base)
    # Use a sentinel key for market-wide rows so UNIQUE(symbol_key, period_date, period_scope)
    # can deduplicate via ON CONFLICT.
    feat["symbol_key"] = -1
    feat["period_scope"] = "market"
    return feat


def upsert_news_sentiment_daily(engine, df):
    if df.empty:
        return 0

    rows = df[
        [
            "symbol_key",
            "period_date",
            "period_scope",
            "sentiment_score_t1",
            "sentiment_score_t3",
            "sentiment_score_t7",
            "good_cnt_t1",
            "good_cnt_t3",
            "good_cnt_t7",
            "bad_cnt_t1",
            "bad_cnt_t3",
            "bad_cnt_t7",
            "coverage_t1",
            "coverage_t3",
            "coverage_t7",
        ]
    ].replace({np.nan: None})

    sql = text(
        f"""
        INSERT INTO {DB_SCHEMA_DWH}.fact_news_sentiment_daily (
            symbol_key, period_date, period_scope,
            sentiment_score_t1, sentiment_score_t3, sentiment_score_t7,
            good_cnt_t1, good_cnt_t3, good_cnt_t7,
            bad_cnt_t1, bad_cnt_t3, bad_cnt_t7,
            coverage_t1, coverage_t3, coverage_t7,
            updated_at
        ) VALUES (
            :symbol_key, :period_date, :period_scope,
            :sentiment_score_t1, :sentiment_score_t3, :sentiment_score_t7,
            :good_cnt_t1, :good_cnt_t3, :good_cnt_t7,
            :bad_cnt_t1, :bad_cnt_t3, :bad_cnt_t7,
            :coverage_t1, :coverage_t3, :coverage_t7,
            now()
        )
        ON CONFLICT (symbol_key, period_date, period_scope)
        DO UPDATE SET
            sentiment_score_t1 = EXCLUDED.sentiment_score_t1,
            sentiment_score_t3 = EXCLUDED.sentiment_score_t3,
            sentiment_score_t7 = EXCLUDED.sentiment_score_t7,
            good_cnt_t1 = EXCLUDED.good_cnt_t1,
            good_cnt_t3 = EXCLUDED.good_cnt_t3,
            good_cnt_t7 = EXCLUDED.good_cnt_t7,
            bad_cnt_t1 = EXCLUDED.bad_cnt_t1,
            bad_cnt_t3 = EXCLUDED.bad_cnt_t3,
            bad_cnt_t7 = EXCLUDED.bad_cnt_t7,
            coverage_t1 = EXCLUDED.coverage_t1,
            coverage_t3 = EXCLUDED.coverage_t3,
            coverage_t7 = EXCLUDED.coverage_t7,
            updated_at = now()
        """
    )

    with engine.begin() as conn:
        conn.execute(sql, rows.to_dict(orient="records"))
    return len(rows)


def upsert_fact_metric_news(engine, symbol_df, market_df):
    if symbol_df.empty and market_df.empty:
        return 0

    metric_rows = []
    for _, row in symbol_df.iterrows():
        for src_col, metric_code in NEWS_METRIC_MAP.items():
            metric_rows.append(
                {
                    "symbol_key": int(row["symbol_key"]),
                    "period_date": row["period_date"],
                    "period_type": "daily",
                    "metric_code": metric_code,
                    "metric_value": float(row[src_col]) if row[src_col] is not None else 0.0,
                }
            )

    if not market_df.empty and not symbol_df.empty:
        market_lookup = {
            pd.to_datetime(r["period_date"]).date(): r for _, r in market_df.iterrows()
        }
        for _, row in symbol_df.iterrows():
            period_date = pd.to_datetime(row["period_date"]).date()
            if period_date not in market_lookup:
                continue
            mrow = market_lookup[period_date]
            for src_col, metric_code in MARKET_METRIC_MAP.items():
                metric_rows.append(
                    {
                        "symbol_key": int(row["symbol_key"]),
                        "period_date": period_date,
                        "period_type": "daily",
                        "metric_code": metric_code,
                        "metric_value": float(mrow[src_col]) if mrow[src_col] is not None else 0.0,
                    }
                )

    if not metric_rows:
        return 0

    metric_df = pd.DataFrame(metric_rows)
    min_date = metric_df["period_date"].min()
    max_date = metric_df["period_date"].max()
    metric_codes = sorted(metric_df["metric_code"].unique().tolist())

    with engine.begin() as conn:
        for metric_code in metric_codes:
            conn.execute(
                text(
                    f"""
                    DELETE FROM {DB_SCHEMA_DWH}.fact_metric
                    WHERE period_type = 'daily'
                      AND period_date >= :min_date
                      AND period_date <= :max_date
                      AND metric_code = :metric_code
                    """
                ),
                {"min_date": min_date, "max_date": max_date, "metric_code": metric_code},
            )

        insert_sql = text(
            f"""
            INSERT INTO {DB_SCHEMA_DWH}.fact_metric (
                symbol_key,
                period_date,
                period_type,
                metric_key,
                metric_code,
                metric_value,
                is_ml_feature,
                created_at
            )
            SELECT
                :symbol_key,
                :period_date,
                :period_type,
                d.metric_key,
                :metric_code,
                :metric_value,
                d.is_ml_feature,
                now()
            FROM {DB_SCHEMA_DWH}.dim_metric d
            WHERE d.metric_code = :metric_code
            """
        )
        conn.execute(insert_sql, metric_df.to_dict(orient="records"))

    return len(metric_df)


def ensure_dim_metric_news_codes(engine):
    rows = []
    for metric_code in NEWS_METRIC_MAP.values():
        rows.append(
            {
                "metric_code": metric_code,
                "metric_group": "news",
                "unit": "score" if "score" in metric_code else "count",
                "description": metric_code,
                "is_ml_feature": True,
            }
        )
    for metric_code in MARKET_METRIC_MAP.values():
        rows.append(
            {
                "metric_code": metric_code,
                "metric_group": "news_market",
                "unit": "score",
                "description": metric_code,
                "is_ml_feature": True,
            }
        )

    sql = text(
        f"""
        INSERT INTO {DB_SCHEMA_DWH}.dim_metric (
            metric_code, metric_group, unit, description, is_ml_feature
        )
        SELECT
            :metric_code, :metric_group, :unit, :description, :is_ml_feature
        WHERE NOT EXISTS (
            SELECT 1
            FROM {DB_SCHEMA_DWH}.dim_metric d
            WHERE d.metric_code = :metric_code
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, rows)


def main():
    parser = argparse.ArgumentParser(description="Build daily news sentiment features")
    parser.add_argument("--days-back", type=int, default=45, help="Rebuild window in last N days")
    args = parser.parse_args()

    engine = get_engine()
    trade_dates = load_trade_dates(engine, args.days_back)
    if trade_dates.empty:
        print("No trade dates found. Skip.")
        return

    min_date = pd.to_datetime(trade_dates["period_date"]).dt.date.min() - timedelta(days=7)
    symbols = load_active_symbols(engine)
    symbol_news_daily = load_symbol_news_daily(engine, min_date)
    market_news_daily = load_market_news_daily(engine, min_date)

    symbol_features = build_symbol_features(trade_dates, symbols, symbol_news_daily)
    market_features = build_market_features(trade_dates, market_news_daily)

    ensure_dim_metric_news_codes(engine)
    upsert_count = upsert_news_sentiment_daily(
        engine, pd.concat([symbol_features, market_features], ignore_index=True)
    )
    metric_count = upsert_fact_metric_news(engine, symbol_features, market_features)

    print(f"Upserted dwh.fact_news_sentiment_daily rows: {upsert_count}")
    print(f"Upserted dwh.fact_metric news rows: {metric_count}")


if __name__ == "__main__":
    main()
