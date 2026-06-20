{{ config(materialized='view') }}

select
    id,
    metric_pair,
    item_a,
    item_b,
    support_count,
    coverage_count,
    win_count,
    win_rate,
    baseline_win_rate,
    lift_vs_baseline,
    predicted_label,
    model_version,
    created_at
from {{ source('dwh', 'fact_feature_pair_signal') }}

