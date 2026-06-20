import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


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


def rebuild_fact_decision() -> None:
    dwh = os.getenv("DB_SCHEMA_DWH")
    if not dwh:
        raise ValueError("DB_SCHEMA_DWH is not set")

    sql = f"""
    BEGIN;

    ALTER TABLE {dwh}.fact_decision
        DROP CONSTRAINT IF EXISTS fact_decision_predicted_label_check,
        DROP CONSTRAINT IF EXISTS fact_decision_actual_direction_check;

    TRUNCATE TABLE {dwh}.fact_decision RESTART IDENTITY;

    ALTER TABLE {dwh}.fact_decision
        ADD CONSTRAINT fact_decision_predicted_label_check
            CHECK (predicted_label IN ('BUY', 'SELL', 'HOLD')),
        ADD CONSTRAINT fact_decision_actual_direction_check
            CHECK (actual_direction IN ('BUY', 'SELL', 'HOLD'));

    WITH metric_wide AS (
        SELECT
            symbol_key,
            period_date,
            max(metric_value) FILTER (WHERE metric_code = 'obv') AS obv,
            max(metric_value) FILTER (WHERE metric_code = 'obv_ma_20') AS obv_ma_20,
            max(metric_value) FILTER (WHERE metric_code = 'rsi_14') AS rsi_14,
            max(metric_value) FILTER (WHERE metric_code = 'bb_percent_b_20') AS bb_percent_b_20,
            max(metric_value) FILTER (WHERE metric_code = 'bb_upper_20') AS bb_upper_20,
            max(metric_value) FILTER (WHERE metric_code = 'vol_ratio_20') AS vol_ratio_20,
            max(metric_value) FILTER (WHERE metric_code = 'return_1d') AS return_1d,
            max(metric_value) FILTER (WHERE metric_code = 'atr_14') AS atr_14,
            max(metric_value) FILTER (WHERE metric_code = 'atr_ma_14') AS atr_ma_14,
            max(metric_value) FILTER (WHERE metric_code = 'return_5d') AS return_5d,
            max(metric_value) FILTER (WHERE metric_code = 'return_3d') AS return_3d,
            max(metric_value) FILTER (WHERE metric_code = 'high_10d') AS high_10d,
            max(metric_value) FILTER (WHERE metric_code = 'volume') AS volume,
            max(metric_value) FILTER (WHERE metric_code = 'vol_ma_5') AS vol_ma_5,
            max(metric_value) FILTER (WHERE metric_code = 'bb_width_20') AS bb_width_20,
            max(metric_value) FILTER (WHERE metric_code = 'macd_hist') AS macd_hist,
            max(metric_value) FILTER (WHERE metric_code = 'close_price') AS close_price
        FROM {dwh}.fact_metric
        WHERE period_type = 'daily'
          AND metric_code IN (
              'obv',
              'obv_ma_20',
              'rsi_14',
              'bb_percent_b_20',
              'bb_upper_20',
              'vol_ratio_20',
              'return_1d',
              'atr_14',
              'atr_ma_14',
              'return_5d',
              'return_3d',
              'high_10d',
              'volume',
              'vol_ma_5',
              'bb_width_20',
              'macd_hist',
              'close_price'
          )
        GROUP BY symbol_key, period_date
    ),
    buy_metric_history AS (
        SELECT
            metric_wide.*,
            lag(bb_width_20) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_bb_width_20,
            lag(rsi_14, 1) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_rsi_14_1,
            lag(rsi_14, 2) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_rsi_14_2,
            lag(obv, 1) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_obv_1,
            lag(obv, 2) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_obv_2,
            lag(macd_hist, 1) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_macd_hist_1,
            lag(macd_hist, 2) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_macd_hist_2,
            lag(close_price, 1) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_close_price_1,
            lag(close_price, 2) OVER (
                PARTITION BY symbol_key
                ORDER BY period_date
            ) AS prev_close_price_2
        FROM metric_wide
    ),
    buy_flags AS (
        SELECT
            symbol_key,
            period_date,
            (obv < obv_ma_20)::int AS x1,
            (rsi_14 > 70)::int AS x2,
            (bb_percent_b_20 > 1.0)::int AS x3,
            (close_price > bb_upper_20)::int AS x4,
            (vol_ratio_20 > 2 AND return_1d > 0)::int AS x5,
            (atr_14 > atr_ma_14)::int AS x6,
            (return_5d > 0.08)::int AS x7,
            (return_3d > 0.05)::int AS x8,
            (close_price >= high_10d * 0.98)::int AS x9,
            (volume > vol_ma_5 * 1.5)::int AS x10,
            (bb_width_20 > prev_bb_width_20)::int AS x11,
            (rsi_14 < prev_rsi_14_1 AND prev_rsi_14_1 < prev_rsi_14_2)::int AS x12,
            (obv < prev_obv_1 AND prev_obv_1 < prev_obv_2)::int AS x13,
            (macd_hist < prev_macd_hist_1 AND prev_macd_hist_1 < prev_macd_hist_2)::int AS x14,
            (return_1d > 0.04)::int AS x15,
            (close_price > prev_close_price_1 AND prev_close_price_1 > prev_close_price_2)::int AS x16
        FROM buy_metric_history
    ),
    base AS (
        SELECT
            txn.period_date,
            txn.symbol_key,
            upper(txn.actual_signal) AS actual_direction,
            txn.close_price_gt_ma_50 AS sx1,
            txn.ma_20_gt_ma_50 AS sx2,
            txn.close_price_gt_ma_20 AS sx3,
            txn.close_price_gt_ma_15 AS sx4,
            txn.ema_12_gt_ema_26 AS sx5,
            txn.macd_line_gt_signal_line AS sx6,
            txn.volume_gt_vol_ma_20_mul_1_5_and_return_1d_gt_0 AS sx7,
            txn.return_1d_gt_0_and_return_3d_gt_0 AS sx8,
            txn.close_price_gt_bb_upper_20_and_bb_width_20_tang AS sx9,
            txn.close_price_gt_high_10d AS sx10,
            txn.atr_14_gt_atr_ma_14 AS sx11,
            txn.vol_ratio_20_gt_2_0 AS sx12,
            txn.rsi_14_gte_30_and_rsi_14_lt_70 AS sx13,
            txn.return_1d_gt_0 AS sx14,
            txn.vol_ratio_20_gt_1_5 AS sx15,
            txn.vol_lt_ma20_ret_1d_lt_0_close_gt_ma20 AS sx16,
            coalesce(buy_flags.x1, 0) AS bx1,
            coalesce(buy_flags.x2, 0) AS bx2,
            coalesce(buy_flags.x3, 0) AS bx3,
            coalesce(buy_flags.x4, 0) AS bx4,
            coalesce(buy_flags.x5, 0) AS bx5,
            coalesce(buy_flags.x6, 0) AS bx6,
            coalesce(buy_flags.x7, 0) AS bx7,
            coalesce(buy_flags.x8, 0) AS bx8,
            coalesce(buy_flags.x9, 0) AS bx9,
            coalesce(buy_flags.x10, 0) AS bx10,
            coalesce(buy_flags.x11, 0) AS bx11,
            coalesce(buy_flags.x12, 0) AS bx12,
            coalesce(buy_flags.x13, 0) AS bx13,
            coalesce(buy_flags.x14, 0) AS bx14,
            coalesce(buy_flags.x15, 0) AS bx15,
            coalesce(buy_flags.x16, 0) AS bx16
        FROM {dwh}.fact_txn_fp_growth_metrics txn
        LEFT JOIN buy_flags
            ON buy_flags.symbol_key = txn.symbol_key
           AND buy_flags.period_date = txn.period_date
    ),
    matched AS (
        SELECT
            base.symbol_key,
            base.period_date,
            base.actual_direction,
            buy_rule.confidence AS buy_confidence,
            buy_rule.lift AS buy_lift,
            sell_rule.confidence AS sell_confidence,
            sell_rule.lift AS sell_lift
        FROM base
        LEFT JOIN LATERAL (
            SELECT
                rules.confidence,
                rules.lift
            FROM {dwh}.fact_cal_rules_fp_growth_buy rules
            WHERE (rules.x1 = 0 OR base.bx1 = 1)
              AND (rules.x2 = 0 OR base.bx2 = 1)
              AND (rules.x3 = 0 OR base.bx3 = 1)
              AND (rules.x4 = 0 OR base.bx4 = 1)
              AND (rules.x5 = 0 OR base.bx5 = 1)
              AND (rules.x6 = 0 OR base.bx6 = 1)
              AND (rules.x7 = 0 OR base.bx7 = 1)
              AND (rules.x8 = 0 OR base.bx8 = 1)
              AND (rules.x9 = 0 OR base.bx9 = 1)
              AND (rules.x10 = 0 OR base.bx10 = 1)
              AND (rules.x11 = 0 OR base.bx11 = 1)
              AND (rules.x12 = 0 OR base.bx12 = 1)
              AND (rules.x13 = 0 OR base.bx13 = 1)
              AND (rules.x14 = 0 OR base.bx14 = 1)
              AND (rules.x15 = 0 OR base.bx15 = 1)
              AND (rules.x16 = 0 OR base.bx16 = 1)
            ORDER BY
                rules.confidence DESC,
                rules.lift DESC,
                (
                    rules.x1 + rules.x2 + rules.x3 + rules.x4
                    + rules.x5 + rules.x6 + rules.x7 + rules.x8
                    + rules.x9 + rules.x10 + rules.x11 + rules.x12
                    + rules.x13 + rules.x14 + rules.x15 + rules.x16
                ) DESC
            LIMIT 1
        ) buy_rule ON true
        LEFT JOIN LATERAL (
            SELECT
                rules.confidence,
                rules.lift
            FROM {dwh}.fact_cal_rules_fp_growth_sell rules
            WHERE (rules.x1 = 0 OR base.sx1 = 1)
              AND (rules.x2 = 0 OR base.sx2 = 1)
              AND (rules.x3 = 0 OR base.sx3 = 1)
              AND (rules.x4 = 0 OR base.sx4 = 1)
              AND (rules.x5 = 0 OR base.sx5 = 1)
              AND (rules.x6 = 0 OR base.sx6 = 1)
              AND (rules.x7 = 0 OR base.sx7 = 1)
              AND (rules.x8 = 0 OR base.sx8 = 1)
              AND (rules.x9 = 0 OR base.sx9 = 1)
              AND (rules.x10 = 0 OR base.sx10 = 1)
              AND (rules.x11 = 0 OR base.sx11 = 1)
              AND (rules.x12 = 0 OR base.sx12 = 1)
              AND (rules.x13 = 0 OR base.sx13 = 1)
              AND (rules.x14 = 0 OR base.sx14 = 1)
              AND (rules.x15 = 0 OR base.sx15 = 1)
              AND (rules.x16 = 0 OR base.sx16 = 1)
            ORDER BY
                rules.confidence DESC,
                rules.lift DESC,
                (
                    rules.x1 + rules.x2 + rules.x3 + rules.x4
                    + rules.x5 + rules.x6 + rules.x7 + rules.x8
                    + rules.x9 + rules.x10 + rules.x11 + rules.x12
                    + rules.x13 + rules.x14 + rules.x15 + rules.x16
                ) DESC
            LIMIT 1
        ) sell_rule ON true
    ),
    predicted AS (
        SELECT
            symbol_key,
            period_date,
            actual_direction,
            CASE
                WHEN buy_confidence IS NULL AND sell_confidence IS NULL THEN 'HOLD'
                WHEN buy_confidence IS NOT NULL
                     AND (
                         sell_confidence IS NULL
                         OR buy_confidence > sell_confidence
                         OR (buy_confidence = sell_confidence AND buy_lift >= sell_lift)
                     )
                    THEN 'BUY'
                ELSE 'SELL'
            END AS predicted_label
        FROM matched
    )
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
    SELECT
        symbol_key,
        period_date AS trade_date,
        predicted_label,
        actual_direction,
        (predicted_label = actual_direction) AS is_correct,
        NULL::timestamp AS evaluated_at,
        NULL::varchar AS entry_window,
        NULL::time AS entry_time_from,
        NULL::time AS entry_time_to,
        :model_version AS model_version,
        NULL::varchar AS timing_model_version,
        NULL::timestamp AS generated_at
    FROM predicted
    ORDER BY period_date, symbol_key;

    COMMIT;
    """

    with get_engine().begin() as conn:
        result = conn.execute(text(sql), {"model_version": MODEL_VERSION})
        print(f"Rebuilt {dwh}.fact_decision for {MODEL_VERSION}")
        print(f"Inserted rows: {result.rowcount}")


if __name__ == "__main__":
    load_env()
    rebuild_fact_decision()
