import argparse
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert

env_candidates = [
    Path("../../.env"),
]
loaded_env_path = None
for env_candidate in env_candidates:
    if env_candidate.exists():
        load_dotenv(env_candidate)
        loaded_env_path = env_candidate.resolve()
        break

if loaded_env_path is None:
    raise FileNotFoundError("Could not find .env for EDA notebook")

# DB config
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Schema
DWH = os.getenv("DB_SCHEMA_DWH")

# Incremental EDA settings
ROLLING_OBV_WINDOW = 20
TAIL_DAILY_PERIODS = 40


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backfill dwh.fact_cleaned_metric for missing daily dates."
    )
    parser.add_argument("--start-date", required=False, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=False, help="YYYY-MM-DD")
    return parser.parse_args()


def get_db_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


def get_missing_dates(engine, start_date=None, end_date=None):
    filters = []
    params = {}

    if start_date:
        filters.append("and fm.period_date >= :start_date")
        params["start_date"] = pd.Timestamp(start_date).date()
    if end_date:
        filters.append("and fm.period_date <= :end_date")
        params["end_date"] = pd.Timestamp(end_date).date()

    filter_sql = "\n        ".join(filters)
    query = text(
        f"""
        with metric_dates as (
            select distinct period_date
            from {DWH}.fact_metric
            where period_type = 'daily'
        ),
        cleaned_dates as (
            select distinct period_date
            from {DWH}.fact_cleaned_metric
            where period_type = 'daily'
        )
        select fm.period_date
        from metric_dates fm
        left join cleaned_dates fc
          on fm.period_date = fc.period_date
        where fc.period_date is null
        {filter_sql}
        order by fm.period_date
        """
    )
    with engine.connect() as conn:
        result = conn.execute(query, params)
        return [row[0] for row in result.fetchall()]


def load_fact_metric_window(engine, target_date):
    query = text(
        f"""
        with ranked_daily as (
            select
                symbol_key,
                period_date,
                period_type,
                metric_code,
                metric_value,
                dense_rank() over (
                    partition by symbol_key
                    order by period_date desc
                ) as period_rank
            from {DWH}.fact_metric
            where period_type = 'daily'
              and period_date <= :target_date
        )
        select symbol_key, period_date, period_type, metric_code, metric_value
        from ranked_daily
        where period_rank <= {TAIL_DAILY_PERIODS}
        """
    )
    return pd.read_sql(query, engine, params={"target_date": pd.Timestamp(target_date).date()})


def build_cleaned_daily_frame(df):
    df_copy = df.copy()
    df = df_copy

    df_daily = df[df["period_type"] == "daily"]
    df_daily = df_daily.drop(columns=["period_type"])
    df_daily = df_daily.pivot_table(
        index=["symbol_key", "period_date"],
        columns="metric_code",
        values="metric_value",
        aggfunc="first",
    ).reset_index()
    df_daily["period_date"] = pd.to_datetime(df_daily["period_date"])
    df_daily.columns.name = None

    df_daily = df_daily.sort_values(by=["symbol_key", "period_date"]).reset_index(drop=True)

    df_daily["ma_5_norm"] = df_daily["ma_5"] / (df_daily["close_price"] - 1)
    df_daily["ma_9_norm"] = df_daily["ma_9"] / (df_daily["close_price"] - 1)
    df_daily["ma_15_norm"] = df_daily["ma_15"] / (df_daily["close_price"] - 1)
    df_daily["ma_20_norm"] = df_daily["ma_20"] / (df_daily["close_price"] - 1)
    df_daily["ema_12_norm"] = df_daily["ema_12"] / (df_daily["close_price"] - 1)
    df_daily["ema_26_norm"] = df_daily["ema_26"] / (df_daily["close_price"] - 1)
    df_daily["macd_line_norm"] = df_daily["macd_line"] / df_daily["close_price"]
    df_daily["signal_line_norm"] = df_daily["signal_line"] / df_daily["close_price"]
    df_daily["macd_hist_norm"] = df_daily["macd_hist"] / df_daily["close_price"]
    df_daily["bb_width_norm"] = df_daily["bb_width_20"] / df_daily["close_price"]

    obv_roll_mean = df_daily.groupby("symbol_key")["obv"].transform(
        lambda series: series.rolling(ROLLING_OBV_WINDOW, min_periods=ROLLING_OBV_WINDOW).mean()
    )
    obv_roll_std = df_daily.groupby("symbol_key")["obv"].transform(
        lambda series: series.rolling(ROLLING_OBV_WINDOW, min_periods=ROLLING_OBV_WINDOW).std()
    )
    df_daily["obv_zscore"] = (df_daily["obv"] - obv_roll_mean) / obv_roll_std
    df_daily["ma5_vs_ma20"] = df_daily["ma_5"] / df_daily["ma_20"] - 1

    df_daily = df_daily.dropna(subset=["obv_zscore"]).copy()

    df_daily = df_daily.drop(
        columns=[
            "close_price",
            "ma_5",
            "ma_9",
            "ma_15",
            "ma_20",
            "ema_12",
            "ema_26",
            "macd_line",
            "signal_line",
            "macd_hist",
            "bb_upper_20",
            "bb_lower_20",
            "bb_width_20",
            "volume",
            "vol_ma_5",
            "vol_ma_20",
            "obv",
        ]
    )
    return df_daily


def insert_for_date(engine, df_daily, target_date):
    target_ts = pd.Timestamp(target_date)
    df_daily_target = df_daily[df_daily["period_date"] == target_ts].copy()

    if df_daily_target.empty:
        print(f"{target_ts.date()}: no cleaned rows produced, skipping")
        return 0, 0

    df_daily_long = (
        df_daily_target.melt(
            id_vars=["symbol_key", "period_date"],
            var_name="metric_code",
            value_name="metric_value",
        )
        .dropna(subset=["metric_value"])
        .assign(period_type="daily")
    )
    df_daily_long["inserted_at"] = pd.Timestamp.now(tz="UTC").floor("s")

    records = df_daily_long.to_dict(orient="records")
    table = Table("fact_cleaned_metric", MetaData(), schema=DWH, autoload_with=engine)

    chunksize = 5000
    inserted_rows = 0

    with engine.begin() as conn:
        for i in range(0, len(records), chunksize):
            chunk = records[i : i + chunksize]
            stmt = insert(table).values(chunk).on_conflict_do_nothing(
                index_elements=["symbol_key", "period_date", "period_type", "metric_code"]
            )
            result = conn.execute(stmt)
            inserted_rows += result.rowcount

    return inserted_rows, len(records)


def main():
    args = parse_args()
    engine = get_db_engine()

    missing_dates = get_missing_dates(
        engine,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if not missing_dates:
        print("No missing fact_cleaned_metric daily dates found for the requested range.")
        return

    print(f"Found {len(missing_dates)} missing daily dates to backfill.")

    total_inserted = 0
    total_attempted = 0
    for target_date in missing_dates:
        print(f"Backfilling {target_date}...")
        df = load_fact_metric_window(engine, target_date)
        if df.empty:
            print(f"{target_date}: no fact_metric daily rows found, skipping")
            continue

        df_daily = build_cleaned_daily_frame(df)
        inserted_rows, attempted_rows = insert_for_date(engine, df_daily, target_date)
        total_inserted += inserted_rows
        total_attempted += attempted_rows
        print(f"{target_date}: inserted {inserted_rows:,} / attempted {attempted_rows:,}")

    print(
        f"Backfill completed. Inserted {total_inserted:,} new rows / "
        f"{total_attempted:,} attempted across {len(missing_dates)} dates."
    )


if __name__ == "__main__":
    main()
