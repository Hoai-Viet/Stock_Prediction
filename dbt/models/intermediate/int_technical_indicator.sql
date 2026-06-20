-- int_technical_indicator: calculate SMA, EMA, RSI (Wilder's), MACD (EMA-based), Bollinger Bands
-- Also includes volume indicators (volume MA, ratio, OBV) in the same model.

{{ config(
    pre_hook=["{{ create_tech_indicators_fn() }}"]
) }}

with technical_base as (
    select *
    from {{ target.schema }}._calc_tech_indicators_v5()
),

technical_enriched as (
    select
        technical_base.*,
        avg(obv) over (
            partition by symbol_key
            order by trade_date
            rows between 19 preceding and current row
        ) as obv_ma_20,
        avg(atr_14) over (
            partition by symbol_key
            order by trade_date
            rows between 13 preceding and current row
        ) as atr_ma_14,
        lag(volume, 1) over (
            partition by symbol_key
            order by trade_date
        ) as volume_1d,
        lag(volume, 2) over (
            partition by symbol_key
            order by trade_date
        ) as volume_2d,
        max(volume) over (
            partition by symbol_key
            order by trade_date
            rows between 19 preceding and current row
        ) as volume_high_20d,
        lag(
            case
                when rn >= 20 and vol_ma_20 is not null and vol_ma_20 <> 0
                then volume / vol_ma_20
                else null
            end,
            1
        ) over (
            partition by symbol_key
            order by trade_date
        ) as vol_ratio_20_prev,
        lag(
            case
                when rn >= 20 and vol_ma_20 is not null and vol_ma_20 <> 0
                then volume / vol_ma_20
                else null
            end,
            2
        ) over (
            partition by symbol_key
            order by trade_date
        ) as vol_ratio_20_prev2
    from technical_base
)

select
    symbol_key,
    trade_date,

    -- SMA indicators
    case when rn >= 3 then sma_3 else null end as ma_3,
    case when rn >= 5 then sma_5 else null end as ma_5,
    case when rn >= 9 then sma_9 else null end as ma_9,
    case when rn >= 15 then sma_15 else null end as ma_15,
    case when rn >= 20 then sma_20 else null end as ma_20,
    case when rn >= 50 then sma_50 else null end as ma_50,

    -- EMA indicators
    case when rn >= 12 then ema_12 else null end as ema_12,
    case when rn >= 26 then ema_26 else null end as ema_26,

    -- RSI (Wilder's smoothing)
    case
        when rn < 15 then null
        when avg_loss = 0 then 100::numeric
        else 100 - 100 / (1 + avg_gain / nullif(avg_loss, 0))
    end as rsi_14,

    -- MACD (EMA-based)
    case when rn >= 26 then macd_line else null end as macd_line,
    case when rn >= 34 then signal_line else null end as signal_line,
    case when rn >= 34 then signal_line else null end as macd_signal,
    case when rn >= 34 then macd_line - signal_line else null end as macd_hist,

    -- Bollinger Bands (using SMA20, standard)
    case when rn >= 20 then sma_20 + 2 * stddev_20 else null end as bb_upper_20,
    case when rn >= 20 then sma_20 - 2 * stddev_20 else null end as bb_lower_20,
    case when rn >= 20 and sma_20 is not null and sma_20 != 0
         then (4 * stddev_20) / sma_20
         else null
    end as bb_width_20,
    case when rn >= 20 and stddev_20 is not null and stddev_20 != 0
         then (close_price - (sma_20 - 2 * stddev_20)) / (4 * stddev_20)
         else null
    end as bb_percent_b_20,
    case when rn >= 11 then high_10d else null end as high_10d,
    case when rn >= 14 then atr_14 else null end as atr_14,
    case when rn >= 27 then atr_ma_14 else null end as atr_ma_14,

    -- Volume indicators
    volume,
    case when rn >= 5 then vol_ma_5 else null end as vol_ma_5,
    case when rn >= 20 then vol_ma_20 else null end as vol_ma_20,
    case
        when rn >= 20 and vol_ma_20 is not null and vol_ma_20 <> 0
        then volume / vol_ma_20
        else null
    end as vol_ratio_20,
    case
        when rn >= 3 then
            case when volume > volume_1d and volume_1d > volume_2d then 1 else 0 end
        else null
    end as vol_3d_increasing,
    case
        when rn >= 20 then
            case when volume = volume_high_20d then 1 else 0 end
        else null
    end as vol_highest_20d,
    case
        when rn >= 22 then
            case
                when volume / nullif(vol_ma_20, 0) > 2.0
                 and vol_ratio_20_prev < 1.2
                 and vol_ratio_20_prev2 < 1.2
                then 1
                else 0
            end
        else null
    end as vol_accumulation,
    obv,
    case when rn >= 20 then obv_ma_20 else null end as obv_ma_20

from technical_enriched
