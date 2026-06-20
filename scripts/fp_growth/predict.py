import argparse
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


REQUIRED_METRICS = 25
MODEL_VERSION = "model mv_6_6_2026"


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f"Missing .env file: {env_path}")
    load_dotenv(env_path)


def get_engine():
    return create_engine(
        "postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


def next_weekday(day):
    result = day + timedelta(days=1)
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def build_sql(dwh: str) -> str:
    buy_match = " AND ".join(
        f"(rules.x{i} = 0 OR flags.bx{i} = 1)" for i in range(1, 17)
    )
    sell_match = " AND ".join(
        f"(rules.x{i} = 0 OR flags.sx{i} = 1)" for i in range(1, 17)
    )
    rule_size = " + ".join(f"rules.x{i}" for i in range(1, 17))

    return f"""
    WITH metric_wide AS (
        SELECT
            symbol_key,
            period_date,
            max(metric_value) FILTER (WHERE metric_code = 'close_price') AS close_price,
            max(metric_value) FILTER (WHERE metric_code = 'ma_15') AS ma_15,
            max(metric_value) FILTER (WHERE metric_code = 'ma_20') AS ma_20,
            max(metric_value) FILTER (WHERE metric_code = 'ma_50') AS ma_50,
            max(metric_value) FILTER (WHERE metric_code = 'ema_12') AS ema_12,
            max(metric_value) FILTER (WHERE metric_code = 'ema_26') AS ema_26,
            max(metric_value) FILTER (WHERE metric_code = 'rsi_14') AS rsi_14,
            max(metric_value) FILTER (WHERE metric_code = 'macd_line') AS macd_line,
            max(metric_value) FILTER (WHERE metric_code = 'signal_line') AS signal_line,
            max(metric_value) FILTER (WHERE metric_code = 'macd_hist') AS macd_hist,
            max(metric_value) FILTER (WHERE metric_code = 'bb_upper_20') AS bb_upper_20,
            max(metric_value) FILTER (WHERE metric_code = 'bb_percent_b_20') AS bb_percent_b_20,
            max(metric_value) FILTER (WHERE metric_code = 'bb_width_20') AS bb_width_20,
            max(metric_value) FILTER (WHERE metric_code = 'high_10d') AS high_10d,
            max(metric_value) FILTER (WHERE metric_code = 'atr_14') AS atr_14,
            max(metric_value) FILTER (WHERE metric_code = 'atr_ma_14') AS atr_ma_14,
            max(metric_value) FILTER (WHERE metric_code = 'volume') AS volume,
            max(metric_value) FILTER (WHERE metric_code = 'vol_ma_5') AS vol_ma_5,
            max(metric_value) FILTER (WHERE metric_code = 'vol_ma_20') AS vol_ma_20,
            max(metric_value) FILTER (WHERE metric_code = 'vol_ratio_20') AS vol_ratio_20,
            max(metric_value) FILTER (WHERE metric_code = 'obv') AS obv,
            max(metric_value) FILTER (WHERE metric_code = 'obv_ma_20') AS obv_ma_20,
            max(metric_value) FILTER (WHERE metric_code = 'return_1d') AS return_1d,
            max(metric_value) FILTER (WHERE metric_code = 'return_3d') AS return_3d,
            max(metric_value) FILTER (WHERE metric_code = 'return_5d') AS return_5d
        FROM {dwh}.fact_metric
        WHERE period_type = 'daily'
        GROUP BY symbol_key, period_date
    ),
    metric_history AS (
        SELECT
            metric_wide.*,
            lag(bb_width_20) OVER w AS prev_bb_width_20,
            lag(rsi_14, 1) OVER w AS prev_rsi_14_1,
            lag(rsi_14, 2) OVER w AS prev_rsi_14_2,
            lag(obv, 1) OVER w AS prev_obv_1,
            lag(obv, 2) OVER w AS prev_obv_2,
            lag(macd_hist, 1) OVER w AS prev_macd_hist_1,
            lag(macd_hist, 2) OVER w AS prev_macd_hist_2,
            lag(close_price, 1) OVER w AS prev_close_price_1,
            lag(close_price, 2) OVER w AS prev_close_price_2
        FROM metric_wide
        WINDOW w AS (PARTITION BY symbol_key ORDER BY period_date)
    ),
    flags AS (
        SELECT
            symbol_key,
            period_date,
            close_price,
            num_nulls(
                close_price, ma_15, ma_20, ma_50, ema_12, ema_26, rsi_14,
                macd_line, signal_line, macd_hist, bb_upper_20,
                bb_percent_b_20, bb_width_20, high_10d, atr_14, atr_ma_14,
                volume, vol_ma_5, vol_ma_20, vol_ratio_20, obv, obv_ma_20,
                return_1d, return_3d, return_5d
            ) AS null_count,
            (obv < obv_ma_20)::int AS bx1,
            (rsi_14 > 70)::int AS bx2,
            (bb_percent_b_20 > 1.0)::int AS bx3,
            (close_price > bb_upper_20)::int AS bx4,
            (vol_ratio_20 > 2 AND return_1d > 0)::int AS bx5,
            (atr_14 > atr_ma_14)::int AS bx6,
            (return_5d > 0.08)::int AS bx7,
            (return_3d > 0.05)::int AS bx8,
            (close_price >= high_10d * 0.98)::int AS bx9,
            (volume > vol_ma_5 * 1.5)::int AS bx10,
            (bb_width_20 > prev_bb_width_20)::int AS bx11,
            (rsi_14 < prev_rsi_14_1 AND prev_rsi_14_1 < prev_rsi_14_2)::int AS bx12,
            (obv < prev_obv_1 AND prev_obv_1 < prev_obv_2)::int AS bx13,
            (
                macd_hist < prev_macd_hist_1
                AND prev_macd_hist_1 < prev_macd_hist_2
            )::int AS bx14,
            (return_1d > 0.04)::int AS bx15,
            (
                close_price > prev_close_price_1
                AND prev_close_price_1 > prev_close_price_2
            )::int AS bx16,
            (close_price > ma_50)::int AS sx1,
            (ma_20 > ma_50)::int AS sx2,
            (close_price > ma_20)::int AS sx3,
            (close_price > ma_15)::int AS sx4,
            (ema_12 > ema_26)::int AS sx5,
            (macd_line > signal_line)::int AS sx6,
            (volume > vol_ma_20 * 1.5 AND return_1d > 0)::int AS sx7,
            (return_1d > 0 AND return_3d > 0)::int AS sx8,
            (
                close_price > bb_upper_20
                AND bb_width_20 > prev_bb_width_20
            )::int AS sx9,
            (close_price > high_10d)::int AS sx10,
            (atr_14 > atr_ma_14)::int AS sx11,
            (vol_ratio_20 > 2)::int AS sx12,
            (rsi_14 >= 30 AND rsi_14 < 70)::int AS sx13,
            (return_1d > 0)::int AS sx14,
            (vol_ratio_20 > 1.5)::int AS sx15,
            (
                volume < vol_ma_20
                AND return_1d < 0
                AND close_price > ma_20
            )::int AS sx16
        FROM metric_history
        WHERE period_date = :metric_date
    ),
    matched AS (
        SELECT
            flags.symbol_key,
            symbols.symbol_code,
            flags.period_date,
            flags.close_price,
            flags.null_count,
            buy_rule.id AS buy_rule_id,
            buy_rule.antecedents AS buy_combo,
            buy_rule.confidence AS buy_confidence,
            buy_rule.lift AS buy_lift,
            sell_rule.id AS sell_rule_id,
            sell_rule.antecedents AS sell_combo,
            sell_rule.confidence AS sell_confidence,
            sell_rule.lift AS sell_lift
        FROM flags
        JOIN staging.dim_symbol symbols USING (symbol_key)
        LEFT JOIN LATERAL (
            SELECT rules.*
            FROM {dwh}.fact_cal_rules_fp_growth_buy rules
            WHERE rules.confidence >= 0.7
              AND {buy_match}
            ORDER BY
                rules.confidence DESC,
                rules.lift DESC,
                ({rule_size}) DESC
            LIMIT 1
        ) buy_rule ON true
        LEFT JOIN LATERAL (
            SELECT rules.*
            FROM {dwh}.fact_cal_rules_fp_growth_sell rules
            WHERE rules.confidence >= 0.7
              AND {sell_match}
            ORDER BY
                rules.confidence DESC,
                rules.lift DESC,
                ({rule_size}) DESC
            LIMIT 1
        ) sell_rule ON true
    )
    SELECT
        symbol_code,
        symbol_key,
        period_date,
        close_price,
        null_count,
        CASE
            WHEN null_count > 0 THEN 'HOLD'
            WHEN buy_confidence IS NULL AND sell_confidence IS NULL THEN 'HOLD'
            WHEN buy_confidence IS NOT NULL
                 AND (
                     sell_confidence IS NULL
                     OR buy_confidence > sell_confidence
                     OR (
                         buy_confidence = sell_confidence
                         AND buy_lift >= sell_lift
                     )
                 )
                THEN 'BUY'
            ELSE 'SELL'
        END AS prediction,
        buy_rule_id,
        buy_combo,
        buy_confidence,
        buy_lift,
        sell_rule_id,
        sell_combo,
        sell_confidence,
        sell_lift
    FROM matched
    ORDER BY
        CASE
            WHEN buy_confidence IS NULL AND sell_confidence IS NULL THEN 3
            WHEN buy_confidence IS NOT NULL
                 AND (
                     sell_confidence IS NULL
                     OR buy_confidence > sell_confidence
                     OR (
                         buy_confidence = sell_confidence
                         AND buy_lift >= sell_lift
                     )
                 )
                THEN 1
            ELSE 2
        END,
        symbol_code
    """


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict the next trading session from FP-growth rules."
    )
    parser.add_argument(
        "--date",
        help="Metric date in YYYY-MM-DD. Defaults to latest daily metric date.",
    )
    parser.add_argument(
        "--signals-only",
        action="store_true",
        help="Only print BUY and SELL rows.",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Upsert the prediction batch into dwh.fact_decision.",
    )
    parser.add_argument(
        "--model-version",
        default=MODEL_VERSION,
        help=f"Model version stored in fact_decision. Default: {MODEL_VERSION}",
    )
    parser.add_argument(
        "--update-actuals",
        action="store_true",
        help=(
            "Update actual_direction/is_correct for old prediction batches "
            "using next-session close_price, same logic as tomorrow_up."
        ),
    )
    parser.add_argument(
        "--actual-date",
        help="Only update one predicted trade_date in YYYY-MM-DD.",
    )
    return parser.parse_args()


def format_number(value, digits=4):
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def signal_strength(prediction, confidence):
    if prediction == "HOLD" or confidence is None:
        return "HOLD"
    return "CERTAIN" if float(confidence) >= 0.7 else "LIKELY"


def write_predictions(
    engine,
    dwh: str,
    rows,
    prediction_date,
    model_version: str,
) -> int:
    sql = text(
        f"""
        INSERT INTO {dwh}.fact_decision (
            symbol_key,
            trade_date,
            predicted_label,
            actual_direction,
            is_correct,
            evaluated_at,
            entry_window,
            entry_time_from,
            entry_time_to,
            model_version,
            timing_model_version,
            generated_at
        )
        VALUES (
            :symbol_key,
            :trade_date,
            :predicted_label,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            :model_version,
            NULL,
            current_timestamp
        )
        ON CONFLICT (symbol_key, trade_date, model_version)
        DO NOTHING
        """
    )
    params = [
        {
            "symbol_key": row["symbol_key"],
            "trade_date": prediction_date,
            "predicted_label": row["prediction"],
            "model_version": model_version,
        }
        for row in rows
    ]
    with engine.begin() as conn:
        result = conn.execute(sql, params)
    return result.rowcount


def update_actuals(engine, dwh: str, model_version: str, actual_date=None) -> int:
    date_filter = (
        "AND decision.trade_date = :actual_date"
        if actual_date
        else "AND decision.trade_date >= current_date - interval '120 day'"
    )
    sql = text(
        f"""
        WITH decision_signal AS (
            SELECT
                decision.id,
                decision.symbol_key,
                decision.trade_date,
                decision.predicted_label,
                signal_metric.period_date AS signal_date,
                actual_metric.period_date AS actual_date,
                signal_metric.metric_value AS signal_close,
                actual_metric.metric_value AS actual_close
            FROM {dwh}.fact_decision decision
            JOIN LATERAL (
                SELECT metric.period_date, metric.metric_value
                FROM {dwh}.fact_metric metric
                WHERE metric.symbol_key = decision.symbol_key
                  AND metric.period_type = 'daily'
                  AND metric.metric_code = 'close_price'
                  AND metric.period_date = decision.trade_date
                LIMIT 1
            ) actual_metric ON true
            JOIN LATERAL (
                SELECT metric.period_date, metric.metric_value
                FROM {dwh}.fact_metric metric
                WHERE metric.symbol_key = decision.symbol_key
                  AND metric.period_type = 'daily'
                  AND metric.metric_code = 'close_price'
                  AND metric.period_date < decision.trade_date
                ORDER BY metric.period_date DESC
                LIMIT 1
            ) signal_metric ON true
            WHERE decision.model_version = :model_version
              AND decision.predicted_label IN ('BUY', 'SELL')
              {date_filter}
        ),
        actuals AS (
            SELECT
                id,
                CASE
                    WHEN actual_close > signal_close THEN 'BUY'
                    ELSE 'SELL'
                END AS actual_direction
            FROM decision_signal
            WHERE actual_date = trade_date
              AND signal_close IS NOT NULL
              AND actual_close IS NOT NULL
        )
        UPDATE {dwh}.fact_decision decision
        SET
            actual_direction = actuals.actual_direction,
            is_correct = (decision.predicted_label = actuals.actual_direction),
            evaluated_at = current_timestamp
        FROM actuals
        WHERE decision.id = actuals.id
          AND (
              decision.actual_direction IS DISTINCT FROM actuals.actual_direction
              OR decision.is_correct IS DISTINCT FROM (
                  decision.predicted_label = actuals.actual_direction
              )
          )
        """
    )
    params = {"model_version": model_version}
    if actual_date:
        params["actual_date"] = actual_date
    with engine.begin() as conn:
        result = conn.execute(sql, params)
    return result.rowcount


def main() -> None:
    args = parse_args()
    load_env()
    dwh = os.getenv("DB_SCHEMA_DWH")
    if not dwh:
        raise ValueError("DB_SCHEMA_DWH is not set")

    engine = get_engine()
    with engine.connect() as conn:
        metric_date = args.date
        if metric_date is None:
            metric_date = conn.execute(
                text(
                    f"""
                    SELECT max(period_date)
                    FROM {dwh}.fact_metric
                    WHERE period_type = 'daily'
                    """
                )
            ).scalar_one()

        rows = conn.execute(
            text(build_sql(dwh)),
            {"metric_date": metric_date},
        ).mappings().all()

    if not rows:
        raise ValueError(f"No daily metrics found for {metric_date}")

    metric_date = rows[0]["period_date"]
    prediction_date = next_weekday(metric_date)
    incomplete = [row for row in rows if row["null_count"] > 0]
    if incomplete:
        symbols = ", ".join(row["symbol_code"] for row in incomplete)
        print(f"WARNING: incomplete metrics for: {symbols}")

    output_rows = [
        row
        for row in rows
        if not args.signals_only or row["prediction"] != "HOLD"
    ]
    counts = {
        label: sum(row["prediction"] == label for row in rows)
        for label in ("BUY", "SELL", "HOLD")
    }

    if args.write_db:
        written = write_predictions(
            engine=engine,
            dwh=dwh,
            rows=rows,
            prediction_date=prediction_date,
            model_version=args.model_version,
        )
        print(
            f"DB batch       : upserted {written} rows into "
            f"{dwh}.fact_decision ({args.model_version})"
        )

    if args.update_actuals:
        updated = update_actuals(
            engine=engine,
            dwh=dwh,
            model_version=args.model_version,
            actual_date=args.actual_date,
        )
        scope = args.actual_date or "all available batches"
        print(f"Actual update  : updated {updated} rows for {scope}")

    print(f"Metric date    : {metric_date}")
    print(f"Prediction date: {prediction_date}")
    print(
        f"Summary        : BUY={counts['BUY']} "
        f"SELL={counts['SELL']} HOLD={counts['HOLD']}"
    )
    print()
    print(
        f"{'SYMBOL':<8} {'PRED':<6} {'SIGNAL':<8} {'CLOSE':>12} "
        f"{'CONF':>8} {'LIFT':>8} RULE"
    )
    print("-" * 100)

    for row in output_rows:
        if row["prediction"] == "BUY":
            confidence = row["buy_confidence"]
            lift = row["buy_lift"]
            combo = row["buy_combo"]
        elif row["prediction"] == "SELL":
            confidence = row["sell_confidence"]
            lift = row["sell_lift"]
            combo = row["sell_combo"]
        else:
            confidence = None
            lift = None
            combo = ""

        print(
            f"{row['symbol_code']:<8} "
            f"{row['prediction']:<6} "
            f"{signal_strength(row['prediction'], confidence):<8} "
            f"{format_number(row['close_price'], 0):>12} "
            f"{format_number(confidence):>8} "
            f"{format_number(lift):>8} "
            f"{combo or ''}"
        )


if __name__ == "__main__":
    main()
