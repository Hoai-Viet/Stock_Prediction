-- Fail when daily price aggregate emits duplicate rows per symbol/day.
select
    symbol_key,
    trade_date,
    count(*) as row_count
from {{ ref('int_price_daily') }}
group by 1, 2
having count(*) > 1
