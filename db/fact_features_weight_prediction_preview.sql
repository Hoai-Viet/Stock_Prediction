-- Build wide-format rule-based buy/sell input data for next-day prediction.
-- Rule weights and descriptions are read from dwh.fact_features_weight.

WITH params AS (
    SELECT 0.75::numeric AS buy_threshold
),
metric_wide AS (
    SELECT
        symbol_key,
        period_date,
        max(metric_value) FILTER (WHERE metric_code = 'close_price') AS close_price,
        max(metric_value) FILTER (WHERE metric_code = 'volume') AS volume,
        max(metric_value) FILTER (WHERE metric_code = 'vol_ma_20') AS vol_ma_20,
        max(metric_value) FILTER (WHERE metric_code = 'vol_ratio_20') AS vol_ratio_20,
        max(metric_value) FILTER (WHERE metric_code = 'ema_12') AS ema_12,
        max(metric_value) FILTER (WHERE metric_code = 'ema_26') AS ema_26,
        max(metric_value) FILTER (WHERE metric_code = 'macd_line') AS macd_line,
        max(metric_value) FILTER (WHERE metric_code = 'macd_signal') AS macd_signal,
        max(metric_value) FILTER (WHERE metric_code = 'bb_width_20') AS bb_width_20,
        max(metric_value) FILTER (WHERE metric_code = 'bb_upper_20') AS bb_upper_20,
        max(metric_value) FILTER (WHERE metric_code = 'bb_lower_20') AS bb_lower_20,
        max(metric_value) FILTER (WHERE metric_code = 'high_10d') AS high_10d,
        max(metric_value) FILTER (WHERE metric_code = 'atr_14') AS atr_14,
        max(metric_value) FILTER (WHERE metric_code = 'atr_ma_14') AS atr_ma_14,
        max(metric_value) FILTER (WHERE metric_code = 'rsi_14') AS rsi_14,
        max(metric_value) FILTER (WHERE metric_code = 'ma_15') AS ma_15,
        max(metric_value) FILTER (WHERE metric_code = 'ma_20') AS ma_20,
        max(metric_value) FILTER (WHERE metric_code = 'ma_50') AS ma_50,
        max(metric_value) FILTER (WHERE metric_code = 'return_1d') AS return_1d,
        max(metric_value) FILTER (WHERE metric_code = 'return_3d') AS return_3d
    FROM dwh.fact_metric
    WHERE period_type = 'daily'
      AND metric_code IN (
          'close_price',
          'volume',
          'vol_ma_20',
          'vol_ratio_20',
          'ema_12',
          'ema_26',
          'macd_line',
          'macd_signal',
          'bb_width_20',
          'bb_upper_20',
          'bb_lower_20',
          'high_10d',
          'atr_14',
          'atr_ma_14',
          'rsi_14',
          'ma_15',
          'ma_20',
          'ma_50',
          'return_1d',
          'return_3d'
      )
    GROUP BY symbol_key, period_date
),
metric_history AS (
    SELECT
        metric_wide.*,
        lag(bb_width_20) OVER (
            PARTITION BY symbol_key
            ORDER BY period_date
        ) AS prev_bb_width_20,
        lead(close_price) OVER (
            PARTITION BY symbol_key
            ORDER BY period_date
        ) AS next_close_price
    FROM metric_wide
),
rule_flags AS (
    SELECT
        metric_history.symbol_key,
        metric_history.period_date,
        metric_history.close_price,
        metric_history.next_close_price,
        rule_eval.rank_no,
        coalesce(rule_eval.is_match, false) AS is_match
    FROM metric_history
    CROSS JOIN LATERAL (
        VALUES
            (1, close_price > ma_50),
            (2, ma_20 > ma_50),
            (3, close_price > ma_20),
            (4, close_price > ma_15),
            (5, ema_12 > ema_26),
            (6, macd_line > macd_signal),
            (7, volume > vol_ma_20 * 1.5 AND return_1d > 0),
            (8, return_1d > 0 AND return_3d > 0),
            (9, close_price > bb_upper_20 AND bb_width_20 > prev_bb_width_20),
            (10, close_price > high_10d),
            (11, atr_14 > atr_ma_14),
            (12, vol_ratio_20 > 2.0),
            (13, rsi_14 >= 30 AND rsi_14 < 70),
            (14, return_1d > 0),
            (15, vol_ratio_20 > 1.5),
            (16, volume < vol_ma_20 AND return_1d < 0 AND close_price > ma_20)
    ) AS rule_eval(rank_no, is_match)
    WHERE metric_history.close_price IS NOT NULL
      AND metric_history.next_close_price IS NOT NULL
),
scored AS (
    SELECT
        rule_flags.symbol_key,
        rule_flags.period_date,
        rule_flags.close_price,
        rule_flags.next_close_price,
        sum(
            CASE
                WHEN rule_flags.is_match THEN coalesce(fw.weight, 0)
                ELSE 0
            END
        ) AS rule_weight_total,
        max(CASE WHEN rule_flags.rank_no = 1 THEN rule_flags.is_match::int ELSE 0 END) AS close_price_gt_ma_50,
        max(CASE WHEN rule_flags.rank_no = 2 THEN rule_flags.is_match::int ELSE 0 END) AS ma_20_gt_ma_50,
        max(CASE WHEN rule_flags.rank_no = 3 THEN rule_flags.is_match::int ELSE 0 END) AS close_price_gt_ma_20,
        max(CASE WHEN rule_flags.rank_no = 4 THEN rule_flags.is_match::int ELSE 0 END) AS close_price_gt_ma_15,
        max(CASE WHEN rule_flags.rank_no = 5 THEN rule_flags.is_match::int ELSE 0 END) AS ema_12_gt_ema_26,
        max(CASE WHEN rule_flags.rank_no = 6 THEN rule_flags.is_match::int ELSE 0 END) AS macd_line_gt_signal_line,
        max(CASE WHEN rule_flags.rank_no = 7 THEN rule_flags.is_match::int ELSE 0 END) AS volume_gt_vol_ma_20_mul_1_5_and_return_1d_gt_0,
        max(CASE WHEN rule_flags.rank_no = 8 THEN rule_flags.is_match::int ELSE 0 END) AS return_1d_gt_0_and_return_3d_gt_0,
        max(CASE WHEN rule_flags.rank_no = 9 THEN rule_flags.is_match::int ELSE 0 END) AS close_price_gt_bb_upper_20_and_bb_width_20_tang,
        max(CASE WHEN rule_flags.rank_no = 10 THEN rule_flags.is_match::int ELSE 0 END) AS close_price_gt_high_10d,
        max(CASE WHEN rule_flags.rank_no = 11 THEN rule_flags.is_match::int ELSE 0 END) AS atr_14_gt_atr_ma_14,
        max(CASE WHEN rule_flags.rank_no = 12 THEN rule_flags.is_match::int ELSE 0 END) AS vol_ratio_20_gt_2_0,
        max(CASE WHEN rule_flags.rank_no = 13 THEN rule_flags.is_match::int ELSE 0 END) AS rsi_14_gte_30_and_rsi_14_lt_70,
        max(CASE WHEN rule_flags.rank_no = 14 THEN rule_flags.is_match::int ELSE 0 END) AS return_1d_gt_0,
        max(CASE WHEN rule_flags.rank_no = 15 THEN rule_flags.is_match::int ELSE 0 END) AS vol_ratio_20_gt_1_5,
        max(CASE WHEN rule_flags.rank_no = 16 THEN rule_flags.is_match::int ELSE 0 END) AS vol_lt_ma20_ret_1d_lt_0_close_gt_ma20
    FROM rule_flags
    LEFT JOIN dwh.fact_features_weight fw
        ON fw.rank_no = rule_flags.rank_no
    GROUP BY
        rule_flags.symbol_key,
        rule_flags.period_date,
        rule_flags.close_price,
        rule_flags.next_close_price
),
predicted AS (
    SELECT
        scored.*,
        CASE
            WHEN rule_weight_total >= params.buy_threshold THEN 'buy'
            ELSE 'sell'
        END AS prediction,
        CASE
            WHEN next_close_price > close_price THEN 'buy'
            ELSE 'sell'
        END AS actual_signal
    FROM scored
    CROSS JOIN params
)
SELECT
    period_date,
    symbol_key,
    close_price,
    rule_weight_total,
    prediction,
    CASE WHEN actual_signal = 'buy' THEN 1 ELSE 0 END AS tomorrow_up,
    CASE WHEN prediction = actual_signal THEN 1 ELSE 0 END AS actual,
    actual_signal,
    close_price_gt_ma_50,
    ma_20_gt_ma_50,
    close_price_gt_ma_20,
    close_price_gt_ma_15,
    ema_12_gt_ema_26,
    macd_line_gt_signal_line,
    volume_gt_vol_ma_20_mul_1_5_and_return_1d_gt_0,
    return_1d_gt_0_and_return_3d_gt_0,
    close_price_gt_bb_upper_20_and_bb_width_20_tang,
    close_price_gt_high_10d,
    atr_14_gt_atr_ma_14,
    vol_ratio_20_gt_2_0,
    rsi_14_gte_30_and_rsi_14_lt_70,
    return_1d_gt_0,
    vol_ratio_20_gt_1_5,
    vol_lt_ma20_ret_1d_lt_0_close_gt_ma20
FROM predicted
ORDER BY period_date, symbol_key;
