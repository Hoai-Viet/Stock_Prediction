from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db, DWH, STAGING
from threading import Lock
from time import monotonic

router = APIRouter()

DISPLAY_RULE_MIN_CONFIDENCE = 0.6
HISTORICAL_SYMBOL_CACHE_TTL_SECONDS = 21600
_historical_symbol_cache = {}
_historical_symbol_cache_lock = Lock()


def _is_gt(left, right):
    return left is not None and right is not None and left > right


def _is_gte(left, right):
    return left is not None and right is not None and left >= right


def _build_rule_flags(current, previous, previous_2):
    buy_flags = {
        1: _is_gt(current["obv_ma_20"], current["obv"]),
        2: _is_gt(current["rsi_14"], 70),
        3: _is_gt(current["bb_percent_b_20"], 1.0),
        4: _is_gt(current["close_price"], current["bb_upper_20"]),
        5: _is_gt(current["vol_ratio_20"], 2) and _is_gt(current["return_1d"], 0),
        6: _is_gt(current["atr_14"], current["atr_ma_14"]),
        7: _is_gt(current["return_5d"], 0.08),
        8: _is_gt(current["return_3d"], 0.05),
        9: (
            current["close_price"] is not None
            and current["high_10d"] is not None
            and current["close_price"] >= current["high_10d"] * 0.98
        ),
        10: (
            current["volume"] is not None
            and current["vol_ma_5"] is not None
            and current["volume"] > current["vol_ma_5"] * 1.5
        ),
        11: _is_gt(current["bb_width_20"], previous["bb_width_20"]),
        12: (
            _is_gt(previous["rsi_14"], current["rsi_14"])
            and _is_gt(previous_2["rsi_14"], previous["rsi_14"])
        ),
        13: (
            _is_gt(previous["obv"], current["obv"])
            and _is_gt(previous_2["obv"], previous["obv"])
        ),
        14: (
            _is_gt(previous["macd_hist"], current["macd_hist"])
            and _is_gt(previous_2["macd_hist"], previous["macd_hist"])
        ),
        15: _is_gt(current["return_1d"], 0.04),
        16: (
            _is_gt(current["close_price"], previous["close_price"])
            and _is_gt(previous["close_price"], previous_2["close_price"])
        ),
    }
    sell_flags = {
        1: _is_gt(current["close_price"], current["ma_50"]),
        2: _is_gt(current["ma_20"], current["ma_50"]),
        3: _is_gt(current["close_price"], current["ma_20"]),
        4: _is_gt(current["close_price"], current["ma_15"]),
        5: _is_gt(current["ema_12"], current["ema_26"]),
        6: _is_gt(current["macd_line"], current["signal_line"]),
        7: (
            current["volume"] is not None
            and current["vol_ma_20"] is not None
            and current["volume"] > current["vol_ma_20"] * 1.5
            and _is_gt(current["return_1d"], 0)
        ),
        8: _is_gt(current["return_1d"], 0) and _is_gt(current["return_3d"], 0),
        9: (
            _is_gt(current["close_price"], current["bb_upper_20"])
            and _is_gt(current["bb_width_20"], previous["bb_width_20"])
        ),
        10: _is_gt(current["close_price"], current["high_10d"]),
        11: _is_gt(current["atr_14"], current["atr_ma_14"]),
        12: _is_gt(current["vol_ratio_20"], 2),
        13: (
            _is_gte(current["rsi_14"], 30)
            and current["rsi_14"] is not None
            and current["rsi_14"] < 70
        ),
        14: _is_gt(current["return_1d"], 0),
        15: _is_gt(current["vol_ratio_20"], 1.5),
        16: (
            current["volume"] is not None
            and current["vol_ma_20"] is not None
            and current["return_1d"] is not None
            and current["close_price"] is not None
            and current["ma_20"] is not None
            and current["volume"] < current["vol_ma_20"]
            and current["return_1d"] < 0
            and current["close_price"] > current["ma_20"]
        ),
    }
    return buy_flags, sell_flags


def _best_exact_rule(db, table_name, flags, min_confidence=0.6):
    rules = db.execute(text(f"""
        SELECT
            id,
            antecedents,
            confidence::double precision AS confidence,
            lift::double precision AS lift,
            x1, x2, x3, x4, x5, x6, x7, x8,
            x9, x10, x11, x12, x13, x14, x15, x16
        FROM {DWH}.{table_name}
    """)).mappings().fetchall()
    candidates = []
    for rule in rules:
        confidence = float(rule["confidence"])
        if confidence < min_confidence:
            continue
        required = [index for index in range(1, 17) if rule[f"x{index}"] == 1]
        if all(flags[index] for index in required):
            candidates.append(
                (
                    confidence,
                    float(rule["lift"]),
                    len(required),
                    dict(rule),
                )
            )
    return max(candidates, default=None, key=lambda item: item[:3])


def _historical_high_confidence_sql():
    buy_match = " AND ".join(
        f"(rules.x{index} = 0 OR base.bx{index} = 1)"
        for index in range(1, 17)
    )
    sell_match = " AND ".join(
        f"(rules.x{index} = 0 OR base.sx{index} = 1)"
        for index in range(1, 17)
    )
    rule_size = " + ".join(f"rules.x{index}" for index in range(1, 17))

    return f"""
        WITH latest_historical_date AS (
            SELECT max(trade_date) AS max_trade_date
            FROM {DWH}.fact_decision
            WHERE generated_at IS NULL
        ),
        metric_wide AS (
            SELECT
                symbol_key,
                period_date,
                max(metric_value) FILTER (WHERE metric_code = 'close_price') AS close_price,
                max(metric_value) FILTER (WHERE metric_code = 'rsi_14') AS rsi_14,
                max(metric_value) FILTER (WHERE metric_code = 'macd_hist') AS macd_hist,
                max(metric_value) FILTER (WHERE metric_code = 'bb_upper_20') AS bb_upper_20,
                max(metric_value) FILTER (WHERE metric_code = 'bb_percent_b_20') AS bb_percent_b_20,
                max(metric_value) FILTER (WHERE metric_code = 'bb_width_20') AS bb_width_20,
                max(metric_value) FILTER (WHERE metric_code = 'high_10d') AS high_10d,
                max(metric_value) FILTER (WHERE metric_code = 'atr_14') AS atr_14,
                max(metric_value) FILTER (WHERE metric_code = 'atr_ma_14') AS atr_ma_14,
                max(metric_value) FILTER (WHERE metric_code = 'volume') AS volume,
                max(metric_value) FILTER (WHERE metric_code = 'vol_ma_5') AS vol_ma_5,
                max(metric_value) FILTER (WHERE metric_code = 'vol_ratio_20') AS vol_ratio_20,
                max(metric_value) FILTER (WHERE metric_code = 'obv') AS obv,
                max(metric_value) FILTER (WHERE metric_code = 'obv_ma_20') AS obv_ma_20,
                max(metric_value) FILTER (WHERE metric_code = 'return_1d') AS return_1d,
                max(metric_value) FILTER (WHERE metric_code = 'return_3d') AS return_3d,
                max(metric_value) FILTER (WHERE metric_code = 'return_5d') AS return_5d
            FROM {DWH}.fact_metric
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
                (
                    rsi_14 < prev_rsi_14_1
                    AND prev_rsi_14_1 < prev_rsi_14_2
                )::int AS x12,
                (
                    obv < prev_obv_1
                    AND prev_obv_1 < prev_obv_2
                )::int AS x13,
                (
                    macd_hist < prev_macd_hist_1
                    AND prev_macd_hist_1 < prev_macd_hist_2
                )::int AS x14,
                (return_1d > 0.04)::int AS x15,
                (
                    close_price > prev_close_price_1
                    AND prev_close_price_1 > prev_close_price_2
                )::int AS x16
            FROM metric_history
        ),
        base AS (
            SELECT
                txn.period_date,
                txn.symbol_key,
                upper(txn.actual_signal) AS actual_direction,
                decision.predicted_label,
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
            FROM {DWH}.fact_decision decision
            JOIN {DWH}.fact_txn_fp_growth_metrics txn
                ON txn.symbol_key = decision.symbol_key
               AND txn.period_date = decision.trade_date
            LEFT JOIN buy_flags
                ON buy_flags.symbol_key = txn.symbol_key
               AND buy_flags.period_date = txn.period_date
            CROSS JOIN latest_historical_date latest
            WHERE decision.generated_at IS NULL
              AND decision.predicted_label IN ('BUY', 'SELL')
              AND upper(txn.actual_signal) IN ('BUY', 'SELL')
              AND decision.trade_date >= (
                  latest.max_trade_date - make_interval(months => :months)
              )::date
        ),
        matched AS (
            SELECT
                symbols.symbol_code,
                base.period_date,
                base.actual_direction,
                base.predicted_label,
                coalesce(
                    buy_rule.confidence,
                    sell_rule.confidence
                ) AS rule_confidence
            FROM base
            JOIN staging.dim_symbol symbols USING (symbol_key)
            LEFT JOIN LATERAL (
                SELECT rules.confidence
                FROM {DWH}.fact_cal_rules_fp_growth_buy rules
                WHERE base.predicted_label = 'BUY'
                  AND rules.confidence >= :min_confidence
                  AND {buy_match}
                ORDER BY
                    rules.confidence DESC,
                    rules.lift DESC,
                    ({rule_size}) DESC
                LIMIT 1
            ) buy_rule ON true
            LEFT JOIN LATERAL (
                SELECT rules.confidence
                FROM {DWH}.fact_cal_rules_fp_growth_sell rules
                WHERE base.predicted_label = 'SELL'
                  AND rules.confidence >= :min_confidence
                  AND {sell_match}
                ORDER BY
                    rules.confidence DESC,
                    rules.lift DESC,
                    ({rule_size}) DESC
                LIMIT 1
            ) sell_rule ON true
        ),
        symbol_stats AS (
            SELECT
                symbol_code,
                count(*) AS total_predictions,
                count(*) FILTER (
                    WHERE predicted_label = actual_direction
                ) AS correct_predictions,
                100.0 * count(*) FILTER (
                    WHERE predicted_label = actual_direction
                ) / nullif(count(*), 0) AS accuracy_pct,
                min(period_date) AS first_trade_date,
                max(period_date) AS last_trade_date
            FROM matched
            WHERE predicted_label IN ('BUY', 'SELL')
              AND rule_confidence >= :min_confidence
            GROUP BY symbol_code
        )
        SELECT
            symbol_code,
            total_predictions,
            correct_predictions,
            round(accuracy_pct::numeric, 2) AS accuracy_pct,
            first_trade_date,
            last_trade_date
        FROM symbol_stats
        WHERE total_predictions >= :min_predictions
          AND accuracy_pct >= :min_accuracy
        ORDER BY
            accuracy_pct DESC,
            total_predictions DESC,
            symbol_code
        LIMIT :limit
    """


@router.get("/symbols")
def get_prediction_symbols(db: Session = Depends(get_db)):
    """Symbols that actually have prediction rows."""
    rows = db.execute(text(f"""
        SELECT DISTINCT
            s.symbol_key,
            s.symbol_code,
            s.company_name,
            s.sector_name,
            s.description
        FROM {DWH}.fact_decision d
        JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
        WHERE s.symbol_code IS NOT NULL
        ORDER BY s.symbol_code
    """)).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/historical-high-confidence-symbols")
def get_historical_high_confidence_symbols(
    min_confidence: float = Query(0.7, ge=0, le=1),
    min_accuracy: float = Query(75.0, ge=0, le=100),
    min_predictions: int = Query(1, ge=1),
    months: int = Query(3, ge=2, le=3),
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Combined BUY/SELL accuracy by symbol for predictions matched by strong rules."""
    cache_key = (min_confidence, min_accuracy, min_predictions, months, limit)
    cached = _historical_symbol_cache.get(cache_key)
    if (
        cached
        and monotonic() - cached["created_at"]
        < HISTORICAL_SYMBOL_CACHE_TTL_SECONDS
    ):
        return cached["rows"]

    with _historical_symbol_cache_lock:
        cached = _historical_symbol_cache.get(cache_key)
        if (
            cached
            and monotonic() - cached["created_at"]
            < HISTORICAL_SYMBOL_CACHE_TTL_SECONDS
        ):
            return cached["rows"]

        rows = db.execute(
            text(_historical_high_confidence_sql()),
            {
                "min_confidence": min_confidence,
                "min_accuracy": min_accuracy,
                "min_predictions": min_predictions,
                "months": months,
                "limit": limit,
            },
        ).mappings().fetchall()
        result = [dict(row) for row in rows]
        _historical_symbol_cache[cache_key] = {
            "created_at": monotonic(),
            "rows": result,
        }
        return result


@router.get("/signal-accuracy")
def get_signal_accuracy(
    min_accuracy: float = Query(75.0, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Accuracy of BUY and SELL predictions across all evaluated decisions."""
    rows = db.execute(text(f"""
        SELECT
            d.predicted_label AS signal,
            COUNT(*) AS total_predictions,
            COUNT(*) FILTER (
                WHERE d.predicted_label = d.actual_direction
            ) AS correct_predictions,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE d.predicted_label = d.actual_direction
                ) / NULLIF(COUNT(*), 0),
                2
            ) AS accuracy_pct,
            ROUND(
                100.0 * COUNT(*) FILTER (
                    WHERE d.predicted_label = d.actual_direction
                ) / NULLIF(COUNT(*), 0),
                2
            ) >= :min_accuracy AS meets_threshold
        FROM {DWH}.fact_decision d
        WHERE d.predicted_label IN ('BUY', 'SELL')
          AND d.actual_direction IS NOT NULL
        GROUP BY d.predicted_label
        ORDER BY CASE d.predicted_label WHEN 'BUY' THEN 1 ELSE 2 END
    """), {
        "min_accuracy": min_accuracy,
    }).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/latest")
def get_latest_predictions(
    limit: int = Query(50, le=500),
    label: str = Query(None, description="Filter: BUY, SELL, HOLD"),
    min_confidence: float = Query(None),
    db: Session = Depends(get_db),
):
    """Latest predictions with symbol, label, model version, timestamp."""
    filters = ["1=1"]
    params = {"limit": limit}
    if label:
        filters.append("predicted_label = :label")
        params["label"] = label.upper()

    rows = db.execute(text(f"""
        SELECT
            d.symbol_key,
            s.symbol_code,
            d.trade_date,
            d.predicted_label,
            d.model_version,
            d.generated_at,
            d.is_correct,
            d.actual_direction
        FROM {DWH}.fact_decision d
        LEFT JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
        WHERE {' AND '.join(filters)}
        ORDER BY d.generated_at DESC
        LIMIT :limit
    """), params).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/history-overview")
def get_history_overview(
    limit: int = Query(500, le=1000),
    db: Session = Depends(get_db),
):
    """Confirmed BUY/SELL decisions from the latest two-month window."""
    rows = db.execute(text(f"""
        WITH latest_date AS (
            SELECT MAX(trade_date) AS max_trade_date
            FROM {DWH}.fact_decision
        ),
        target_window AS (
            SELECT
                (max_trade_date - INTERVAL '2 months')::date AS start_date,
                max_trade_date::date AS end_date
            FROM latest_date
        ),
        base_rows AS (
            SELECT
                d.symbol_key,
                s.symbol_code,
                d.trade_date,
                d.predicted_label,
                d.actual_direction,
                d.is_correct,
                d.model_version,
                d.generated_at,
                close_metric.metric_value::double precision AS close_price,
                previous_close.metric_value::double precision AS previous_close
            FROM {DWH}.fact_decision d
            JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
            CROSS JOIN target_window w
            LEFT JOIN LATERAL (
                SELECT metric_value
                FROM {DWH}.fact_metric m
                WHERE m.symbol_key = d.symbol_key
                  AND m.period_date = d.trade_date
                  AND m.period_type = 'daily'
                  AND m.metric_code = 'close_price'
                LIMIT 1
            ) close_metric ON true
            LEFT JOIN LATERAL (
                SELECT metric_value
                FROM {DWH}.fact_metric m
                WHERE m.symbol_key = d.symbol_key
                  AND m.period_date < d.trade_date
                  AND m.period_type = 'daily'
                  AND m.metric_code = 'close_price'
                ORDER BY m.period_date DESC
                LIMIT 1
            ) previous_close ON true
            WHERE d.predicted_label IN ('BUY', 'SELL')
              AND d.actual_direction IS NOT NULL
              AND d.is_correct IS NOT NULL
              AND d.trade_date BETWEEN w.start_date AND w.end_date
        ),
        scored_rows AS (
            SELECT
                symbol_key,
                symbol_code,
                trade_date,
                predicted_label,
                actual_direction,
                is_correct,
                model_version,
                generated_at,
                close_price,
                CASE
                    WHEN close_price IS NOT NULL
                     AND previous_close IS NOT NULL
                     AND previous_close <> 0
                    THEN
                        CASE
                            WHEN predicted_label = 'SELL'
                            THEN ((previous_close - close_price) / previous_close) * 100.0
                            ELSE ((close_price - previous_close) / previous_close) * 100.0
                        END
                    ELSE NULL
                END AS return_pct
            FROM base_rows
        )
        SELECT
            symbol_key,
            symbol_code,
            trade_date,
            predicted_label,
            actual_direction,
            is_correct,
            model_version,
            generated_at,
            close_price,
            return_pct
        FROM scored_rows
        ORDER BY trade_date DESC, symbol_code
        LIMIT :limit
    """), {"limit": limit}).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/financials/{symbol}")
def get_financial_reports(
    symbol: str,
    years: int = Query(5, ge=3, le=10),
    db: Session = Depends(get_db),
):
    """Annual financial-report series used by the prediction dashboard charts."""
    rows = db.execute(text(f"""
        WITH available_years AS (
            SELECT DISTINCT year
            FROM {STAGING}.fact_financials
            WHERE stock_code = UPPER(:symbol)
              AND statement_type = 'year'
              AND period = 0
            ORDER BY year DESC
            LIMIT :years
        )
        SELECT
            financials.year,
            MAX(financials.metric_value::double precision)
                FILTER (WHERE financials.metric_code = 'TONG_THU_NHAP_HOAT_ONG')
                / 1000000000000.0 AS operating_income,
            MAX(financials.metric_value::double precision)
                FILTER (WHERE financials.metric_code = 'THU_NHAP_LAI_THUAN')
                / 1000000000000.0 AS net_interest_income,
            MAX(financials.metric_value::double precision)
                FILTER (WHERE financials.metric_code = 'LOI_NHUAN_SAU_THUE_CUA_CO_ONG_CONG_TY_ME_ONG')
                / 1000000000000.0 AS net_profit,
            MAX(financials.metric_value::double precision)
                FILTER (WHERE financials.metric_code = 'TONG_CONG_TAI_SAN_ONG')
                / 1000000000000.0 AS total_assets,
            MAX(financials.metric_value::double precision)
                FILTER (WHERE financials.metric_code = 'TIEN_GUI_CUA_KHACH_HANG')
                / 1000000000000.0 AS customer_deposits,
            MAX(financials.metric_value::double precision)
                FILTER (
                    WHERE financials.metric_code =
                        'NET_CASH_INFLOWS_OUTFLOWS_FROM_OPERATING_ACTIVITIES'
                )
                / 1000000000000.0 AS operating_cash_flow
        FROM {STAGING}.fact_financials financials
        INNER JOIN available_years ON available_years.year = financials.year
        WHERE financials.stock_code = UPPER(:symbol)
          AND financials.statement_type = 'year'
          AND financials.period = 0
        GROUP BY financials.year
        ORDER BY financials.year
    """), {"symbol": symbol, "years": years}).mappings().fetchall()
    return [dict(row) for row in rows]


@router.get("/technical/{symbol}")
def get_technical_metrics(
    symbol: str,
    limit: int = Query(60, le=250),
    db: Session = Depends(get_db),
):
    """Daily technical indicators from fact_metric for charting."""
    rows = db.execute(text(f"""
        SELECT
            m.period_date,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'close_price') AS close,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'volume') AS volume,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'vol_ma_20') AS vol_avg,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'rsi_14') AS rsi,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'macd_line') AS macd,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'signal_line') AS macd_signal,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'macd_hist') AS macd_hist,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'ma_20') AS ma_20,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'bb_upper_20') AS bb_upper,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'bb_lower_20') AS bb_lower,
            MAX(m.metric_value::double precision) FILTER (WHERE m.metric_code = 'obv') AS obv
        FROM {DWH}.fact_metric m
        JOIN staging.dim_symbol s ON s.symbol_key = m.symbol_key
        WHERE UPPER(s.symbol_code) = UPPER(:symbol)
          AND m.period_type = 'daily'
          AND m.metric_code IN (
              'close_price',
              'volume',
              'vol_ma_20',
              'rsi_14',
              'macd_line',
              'signal_line',
              'macd_hist',
              'ma_20',
              'bb_upper_20',
              'bb_lower_20',
              'obv'
          )
        GROUP BY m.period_date
        ORDER BY m.period_date DESC
        LIMIT :limit
    """), {
        "symbol": symbol,
        "limit": limit,
    }).mappings().fetchall()

    return [dict(r) for r in reversed(rows)]


@router.get("/candles/{symbol}")
def get_price_candles(
    symbol: str,
    period: str = Query("1D", pattern="^(1D|1M|3M|6M|1Y|All)$"),
    db: Session = Depends(get_db),
):
    """Aggregate candles from staging into daily/monthly/quarterly/yearly OHLC candles from 2022."""
    period_config = {
        "1D": {"bucket": "day"},
        "1M": {"bucket": "month"},
        "3M": {"bucket": "quarter"},
        "6M": {"bucket": "half_year"},
        "1Y": {"bucket": "year"},
        "All": {"bucket": "month"},
    }
    config = period_config[period]
    bucket_expr = {
        "day": "trade_date::date",
        "month": "date_trunc('month', trade_date)::date",
        "quarter": "date_trunc('quarter', trade_date)::date",
        "half_year": "(date_trunc('year', trade_date) + CASE WHEN EXTRACT(MONTH FROM trade_date) <= 6 THEN INTERVAL '0 months' ELSE INTERVAL '6 months' END)::date",
        "year": "date_trunc('year', trade_date)::date",
    }[config["bucket"]]

    rows = db.execute(text(f"""
        WITH daily_source AS (
            SELECT
                f.trade_date,
                f.candle_time,
                f.open,
                f.high,
                f.low,
                f.close,
                f.volume
            FROM staging.fact_stock_price_intraday f
            WHERE f.interval_key = 1440
              AND UPPER(f.symbol_code) = UPPER(:symbol)
            UNION ALL
            SELECT
                f.trade_date,
                f.candle_time,
                f.open,
                f.high,
                f.low,
                f.close,
                f.volume
            FROM staging.fact_stock_price_intraday f
            WHERE f.interval_key = 1
              AND UPPER(f.symbol_code) = UPPER(:symbol)
              AND f.trade_date > COALESCE((
                  SELECT MAX(trade_date)
                  FROM staging.fact_stock_price_intraday
                  WHERE interval_key = 1440
                    AND UPPER(symbol_code) = UPPER(:symbol)
              ), DATE '1900-01-01')
        ),
        bucketed AS (
            SELECT
                {bucket_expr} AS bucket_date,
                trade_date,
                candle_time,
                open,
                high,
                low,
                close,
                volume
            FROM daily_source
            WHERE trade_date >= DATE '2022-01-01'
        )
        SELECT
            bucket_date AS time,
            ((ARRAY_AGG(open ORDER BY candle_time ASC))[1]::double precision / 1000.0) AS open,
            (MAX(high)::double precision / 1000.0) AS high,
            (MIN(low)::double precision / 1000.0) AS low,
            ((ARRAY_AGG(close ORDER BY candle_time DESC))[1]::double precision / 1000.0) AS close,
            SUM(volume)::double precision AS volume
        FROM bucketed
        GROUP BY bucket_date
        ORDER BY bucket_date
    """), {"symbol": symbol}).mappings().fetchall()

    return [dict(r) for r in rows]


@router.get("/current/{symbol}")
def get_current_prediction(symbol: str, db: Session = Depends(get_db)):
    decision = db.execute(text(f"""
        SELECT
            d.symbol_key,
            d.trade_date,
            d.predicted_label,
            d.model_version,
            d.generated_at,
            d.is_correct,
            d.actual_direction
        FROM {DWH}.fact_decision d
        JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
        WHERE UPPER(s.symbol_code) = UPPER(:symbol)
        ORDER BY d.trade_date DESC, d.generated_at DESC NULLS LAST, d.id DESC
        LIMIT 1
    """), {"symbol": symbol}).mappings().first()
    if not decision:
        return None

    metrics = db.execute(text(f"""
        WITH metric_dates AS (
            SELECT DISTINCT period_date
            FROM {DWH}.fact_metric
            WHERE symbol_key = :symbol_key
              AND period_type = 'daily'
              AND period_date < :trade_date
            ORDER BY period_date DESC
            LIMIT 3
        )
        SELECT
            metric.period_date,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'close_price') AS close_price,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'ma_15') AS ma_15,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'ma_20') AS ma_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'ma_50') AS ma_50,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'ema_12') AS ema_12,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'ema_26') AS ema_26,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'rsi_14') AS rsi_14,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'macd_line') AS macd_line,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'signal_line') AS signal_line,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'macd_hist') AS macd_hist,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'bb_upper_20') AS bb_upper_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'bb_percent_b_20') AS bb_percent_b_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'bb_width_20') AS bb_width_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'high_10d') AS high_10d,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'atr_14') AS atr_14,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'atr_ma_14') AS atr_ma_14,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'volume') AS volume,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'vol_ma_5') AS vol_ma_5,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'vol_ma_20') AS vol_ma_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'vol_ratio_20') AS vol_ratio_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'obv') AS obv,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'obv_ma_20') AS obv_ma_20,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'return_1d') AS return_1d,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'return_3d') AS return_3d,
            max(metric.metric_value::double precision)
                FILTER (WHERE metric.metric_code = 'return_5d') AS return_5d
        FROM {DWH}.fact_metric metric
        JOIN metric_dates USING (period_date)
        WHERE metric.symbol_key = :symbol_key
          AND metric.period_type = 'daily'
        GROUP BY metric.period_date
        ORDER BY metric.period_date DESC
    """), {
        "symbol_key": decision["symbol_key"],
        "trade_date": decision["trade_date"],
    }).mappings().fetchall()

    if len(metrics) < 3:
        return {
            **dict(decision),
            "predicted_label": "HOLD",
            "signal_strength": "HOLD",
            "close_price": None,
            "confidence": None,
            "rule_id": None,
            "rule_combo": None,
            "display_label": None,
            "display_confidence": None,
            "display_rule_id": None,
            "display_rule_combo": None,
            "missing_feature": None,
        }

    buy_flags, sell_flags = _build_rule_flags(metrics[0], metrics[1], metrics[2])
    display_buy_rule = _best_exact_rule(
        db,
        "fact_cal_rules_fp_growth_buy",
        buy_flags,
        min_confidence=DISPLAY_RULE_MIN_CONFIDENCE,
    )
    display_sell_rule = _best_exact_rule(
        db,
        "fact_cal_rules_fp_growth_sell",
        sell_flags,
        min_confidence=DISPLAY_RULE_MIN_CONFIDENCE,
    )

    display_choices = []
    if display_buy_rule:
        display_choices.append((*display_buy_rule[:3], 1, "BUY", display_buy_rule[3]))
    if display_sell_rule:
        display_choices.append((*display_sell_rule[:3], 0, "SELL", display_sell_rule[3]))

    display_choice = max(display_choices, default=None, key=lambda item: item[:4])
    display_fields = {
        "display_label": display_choice[4] if display_choice else None,
        "display_confidence": display_choice[0] if display_choice else None,
        "display_rule_id": display_choice[5]["id"] if display_choice else None,
        "display_rule_combo": display_choice[5]["antecedents"] if display_choice else None,
    }

    if not display_choice:
        return {
            **dict(decision),
            "predicted_label": "HOLD",
            "signal_strength": "HOLD",
            "close_price": metrics[0]["close_price"],
            "confidence": None,
            "rule_id": None,
            "rule_combo": None,
            **display_fields,
            "missing_feature": None,
        }

    confidence, _, _, _, label, rule = display_choice
    return {
        **dict(decision),
        "predicted_label": label,
        "signal_strength": "CERTAIN" if confidence >= 0.7 else "LIKELY",
        "close_price": metrics[0]["close_price"],
        "confidence": confidence,
        "is_correct": (
            None
            if decision["actual_direction"] is None
            else decision["actual_direction"] == label
        ),
        "rule_id": rule["id"],
        "rule_combo": rule["antecedents"],
        **display_fields,
        "missing_feature": None,
    }


@router.get("/{symbol}")
def get_prediction_detail(symbol: str, db: Session = Depends(get_db)):
    """Prediction detail + last 30 decision rows for a symbol."""
    rows = db.execute(text(f"""
        WITH rule_confidence AS (
            SELECT
                (
                    (
                        SELECT max(confidence)::double precision
                        FROM {DWH}.fact_cal_rules_fp_growth_buy
                        WHERE confidence >= 0.7
                          AND confidence < 0.8
                    )
                    +
                    (
                        SELECT max(confidence)::double precision
                        FROM {DWH}.fact_cal_rules_fp_growth_sell
                        WHERE confidence >= 0.7
                          AND confidence < 0.8
                    )
                ) / 2.0 AS confidence_accuracy
        ),
        decisions AS (
            SELECT
                d.symbol_key,
                d.trade_date,
                d.predicted_label,
                d.model_version,
                d.actual_direction,
                d.is_correct,
                d.generated_at,
                max(d.trade_date) OVER (PARTITION BY d.symbol_key) AS latest_trade_date
            FROM {DWH}.fact_decision d
            JOIN staging.dim_symbol s ON s.symbol_key = d.symbol_key
            WHERE UPPER(s.symbol_code) = UPPER(:symbol)
        ),
        priced AS (
            SELECT
                d.*,
                (actual_close.metric_value::double precision / 1000.0) AS close_price,
                (previous_close.metric_value::double precision / 1000.0) AS previous_close
            FROM decisions d
            LEFT JOIN LATERAL (
                SELECT metric_value
                FROM {DWH}.fact_metric m
                WHERE m.symbol_key = d.symbol_key
                  AND m.period_date = d.trade_date
                  AND m.period_type = 'daily'
                  AND m.metric_code = 'close_price'
                LIMIT 1
            ) actual_close ON true
            LEFT JOIN LATERAL (
                SELECT metric_value
                FROM {DWH}.fact_metric m
                WHERE m.symbol_key = d.symbol_key
                  AND m.period_date < d.trade_date
                  AND m.period_type = 'daily'
                  AND m.metric_code = 'close_price'
                ORDER BY m.period_date DESC
                LIMIT 1
            ) previous_close ON true
        ),
        actionable AS (
            SELECT
                trade_date,
                latest_trade_date,
                predicted_label,
                model_version,
                actual_direction,
                is_correct,
                generated_at,
                close_price,
                rule_confidence.confidence_accuracy,
                CASE
                    WHEN close_price IS NOT NULL AND previous_close IS NOT NULL
                    THEN close_price - previous_close
                    ELSE NULL
                END AS change,
                CASE
                    WHEN close_price IS NOT NULL AND previous_close IS NOT NULL AND previous_close <> 0
                    THEN ((close_price - previous_close) / previous_close) * 100.0
                    ELSE NULL
                END AS change_pct
            FROM priced
            CROSS JOIN rule_confidence
            WHERE predicted_label IN ('BUY', 'SELL')
        ),
        ranked AS (
            SELECT
                actionable.*,
                row_number() OVER (
                    ORDER BY is_correct DESC NULLS LAST, trade_date DESC
                ) AS sort_rank
            FROM actionable
        )
        SELECT
            trade_date,
            latest_trade_date,
            predicted_label,
            model_version,
            actual_direction,
            is_correct,
            generated_at,
            close_price,
            confidence_accuracy,
            change,
            change_pct
        FROM ranked
        WHERE sort_rank <= 30
           OR trade_date = latest_trade_date
        ORDER BY is_correct DESC NULLS LAST, trade_date DESC
    """), {"symbol": symbol}).mappings().fetchall()
    return [dict(r) for r in rows]
