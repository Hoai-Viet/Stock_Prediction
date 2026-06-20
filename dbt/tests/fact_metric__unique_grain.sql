-- Fail when the metric fact has duplicate rows at its declared grain.
select
    symbol_key,
    period_date,
    period_type,
    metric_code,
    count(*) as row_count
from {{ ref('fact_metric') }}
group by 1, 2, 3, 4
having count(*) > 1
