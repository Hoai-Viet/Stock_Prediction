{{ config(
    materialized='incremental',
    unique_key=['symbol_key', 'period_year', 'period_raw', 'report_type', 'statement_type', 'metric_code'],
    on_schema_change='append_new_columns',
    indexes=[
        {'columns': ['symbol_key', 'period_year', 'period_raw', 'report_type', 'statement_type', 'metric_code'], 'unique': true},
        {'columns': ['source_created_at']}
    ]
) }}

{% set min_bctc_year = var('bctc_min_year', env_var('BCTC_MIN_YEAR', '2015')) | int %}
{% set has_source_created_at = false %}
{% if is_incremental() and execute %}
  {% set existing_columns = adapter.get_columns_in_relation(this) %}
  {% set existing_column_names = existing_columns | map(attribute='name') | map('lower') | list %}
  {% set has_source_created_at = 'source_created_at' in existing_column_names %}
{% endif %}

SELECT
    s.symbol_key,
    f.stock_code,
    f.year       AS period_year,
    f.period     AS period_raw,
    f.statement_type,
    CASE
        WHEN f.period = 1 THEN 'Q1'
        WHEN f.period = 2 THEN 'Q2'
        WHEN f.period = 3 THEN 'Q3'
        WHEN f.period = 4 THEN 'Q4'
        WHEN f.period = 0 THEN 'Y'
        ELSE 'Y'   -- period=-1 (quarter fallback) juga dianggap Y cho annual
    END AS period_code,
    f.report_type,
    f.metric_code,
    f.metric_name,
    f.metric_value,
    f.created_at AS source_created_at
FROM {{ source('stg', 'fact_financials') }} f
LEFT JOIN {{ source('stg', 'dim_symbol') }} s
    ON f.stock_code = s.symbol_code
WHERE f.metric_value IS NOT NULL
  AND f.year >= {{ min_bctc_year }}

{% if is_incremental() %}
  {% if has_source_created_at %}
  AND f.created_at >= (
      SELECT COALESCE(MAX(source_created_at), '1900-01-01'::timestamp)
      FROM {{ this }}
  ) - INTERVAL '1 day'
  {% else %}
  AND f.created_at >= CURRENT_TIMESTAMP - INTERVAL '365 day'
  {% endif %}
{% endif %}


