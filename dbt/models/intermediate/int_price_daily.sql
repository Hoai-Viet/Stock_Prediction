-- int_price_daily: aggregate intraday to daily OHLCV

select distinct
    d.symbol_key,
    f.trade_date,

    first_value(f.open) over w as open_price,
    max(f.high) over w as high_price,
    min(f.low) over w as low_price,
    last_value(f.close) over w as close_price,
    sum(f.volume) over w as volume

from {{ source('stg', 'fact_stock_price_intraday') }} f
join {{ source('stg', 'dim_symbol') }} d
  on f.symbol_code = d.symbol_code

window w as (
    partition by d.symbol_key, f.trade_date
    order by f.candle_time
    rows between unbounded preceding and unbounded following
)

