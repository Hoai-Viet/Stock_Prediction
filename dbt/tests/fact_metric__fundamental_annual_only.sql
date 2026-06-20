-- Fail when fundamentals are labeled with a non-annual period type.
with tagged_metrics as (
    select
        f.symbol_key,
        f.period_date,
        f.period_type,
        f.metric_code,
        d.metric_group
    from {{ ref('fact_metric') }} f
    join {{ ref('dim_metric') }} d
      on f.metric_key = d.metric_key
    where d.metric_group in ('balance_sheet', 'income_stmt', 'cash_flow', 'fundamental', 'banking')
)
select *
from tagged_metrics
where period_type <> 'annual'
