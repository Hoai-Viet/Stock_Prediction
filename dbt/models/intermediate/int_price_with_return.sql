-- int_price_with_return: calculate daily returns

select
    symbol_key,
    trade_date,
    close_price,

    close_price::numeric
      / lag(close_price, 1) over (
          partition by symbol_key
          order by trade_date
      ) - 1 as return_1d,

    close_price::numeric
      / lag(close_price, 3) over (
        partition by symbol_key
        order by trade_date
      ) - 1 as return_3d,

    close_price::numeric
      / lag(close_price, 5) over (
          partition by symbol_key
          order by trade_date
      ) - 1 as return_5d,

    lead(close_price, 3) over (
      partition by symbol_key
      order by trade_date
    ) / close_price::numeric - 1 as return_next_3d
from {{ ref('int_price_daily') }}
