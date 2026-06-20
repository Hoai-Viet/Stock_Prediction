{{ config(
    materialized='incremental',
    unique_key=['symbol_key', 'period_date', 'period_type', 'metric_code'],
    schema='dwh',
    on_schema_change='sync_all_columns',
    indexes=[
        {'columns': ['symbol_key', 'period_date', 'period_type', 'metric_code'], 'unique': true},
        {'columns': ['period_type', 'period_date']},
        {'columns': ['source_created_at']}
    ]
) }}

{% set backfill_year = var('backfill_year', none) %}
{% set feature_start_date = var('feature_start_date', none) %}
{% set feature_end_date = var('feature_end_date', none) %}
{% set intraday_feature_only = var('intraday_feature_only', false) %}
{% set backfill_new_technical_metrics = var('backfill_new_technical_metrics', false) %}
{% set new_technical_metrics_start_date = var('new_technical_metrics_start_date', '2010-01-01') %}
{% set has_feature_start = feature_start_date is not none %}
{% set has_feature_end = feature_end_date is not none %}
{% set has_feature_range = has_feature_start and has_feature_end %}

{% if has_feature_start != has_feature_end %}
    {{ exceptions.raise_compiler_error("feature_start_date and feature_end_date must be provided together") }}
{% endif %}

{% if backfill_year is not none and has_feature_range %}
    {{ exceptions.raise_compiler_error("Use either backfill_year or feature_start_date/feature_end_date, not both") }}
{% endif %}

{% set has_source_created_at = false %}
{% if is_incremental() and execute %}
  {% set existing_columns = adapter.get_columns_in_relation(this) %}
  {% set existing_column_names = existing_columns | map(attribute='name') | map('lower') | list %}
  {% set has_source_created_at = 'source_created_at' in existing_column_names %}
{% endif %}

with target_max_dates as (
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    select metric_code, max(period_date) as max_period_date, max(source_created_at) as max_source_created_at
    from {{ this }}
    group by metric_code
    {% else %}
    select
        'dummy' as metric_code,
        '1900-01-01'::date as max_period_date,
        '1900-01-01'::timestamp as max_source_created_at
    {% endif %}
),

raw_metrics as (
    -- PRICE METRICS
    select
        symbol_key,
        trade_date as period_date,
        'daily' as period_type,
        'close_price' as metric_code,
        close_price as metric_value,
        null::timestamp as source_created_at
    from {{ ref('int_price_daily') }}
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    left join target_max_dates t on t.metric_code = 'close_price'
    {% endif %}
    where close_price is not null
    {% if has_feature_range %}
      and trade_date between '{{ feature_start_date }}'::date and '{{ feature_end_date }}'::date
    {% elif backfill_year is not none %}
      and extract(year from trade_date) = {{ backfill_year }}
    {% elif is_incremental() %}
      and trade_date >= coalesce(t.max_period_date, '1900-01-01'::date) - interval '40 day'
    {% endif %}

    union all

    -- RETURN METRICS
    select
        symbol_key,
        trade_date as period_date,
        'daily' as period_type,
        m.metric_code,
        m.metric_value,
        null::timestamp as source_created_at
    from {{ ref('int_price_with_return') }}
    cross join lateral (
        values
            ('return_1d', return_1d),
            ('return_3d', return_3d),
            ('return_5d', return_5d),
            ('return_next_3d', return_next_3d)
    ) as m(metric_code, metric_value)
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    left join target_max_dates t on t.metric_code = m.metric_code
    {% endif %}
    where m.metric_value is not null
    {% if has_feature_range %}
      and trade_date between '{{ feature_start_date }}'::date and '{{ feature_end_date }}'::date
    {% elif backfill_year is not none %}
      and extract(year from trade_date) = {{ backfill_year }}
    {% elif is_incremental() %}
      and trade_date >= (
          select coalesce(min(t2.max_period_date), '1900-01-01'::date) - interval '40 day'
          from (values
              ('return_1d'),
              ('return_3d'),
              ('return_5d'),
              ('return_next_3d')
          ) as v(metric_code)
          left join target_max_dates t2 on v.metric_code = t2.metric_code
      )
      and trade_date >= coalesce(t.max_period_date, '1900-01-01'::date) - interval '40 day'
    {% endif %}

    {% if backfill_new_technical_metrics %}
    union all

    -- MA3 DIRECT BACKFILL
    select
        p.symbol_key,
        p.trade_date as period_date,
        'daily' as period_type,
        'ma_3' as metric_code,
        p.ma_3 as metric_value,
        null::timestamp as source_created_at
    from (
        select
            symbol_key,
            trade_date,
            case
                when row_number() over (
                    partition by symbol_key
                    order by trade_date
                ) >= 3
                then avg(close_price) over (
                    partition by symbol_key
                    order by trade_date
                    rows between 2 preceding and current row
                )
                else null
            end as ma_3
        from {{ ref('int_price_daily') }}
        where close_price is not null
    ) p
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    left join target_max_dates t on t.metric_code = 'ma_3'
    {% endif %}
    where p.ma_3 is not null
      and p.trade_date >= '{{ new_technical_metrics_start_date }}'::date
    {% if has_feature_range %}
      and p.trade_date between '{{ feature_start_date }}'::date and '{{ feature_end_date }}'::date
    {% elif backfill_year is not none %}
      and extract(year from p.trade_date) = {{ backfill_year }}
    {% elif is_incremental() %}
      and p.trade_date >= coalesce(t.max_period_date, '1900-01-01'::date) - interval '40 day'
    {% endif %}
    {% endif %}

    {% if not backfill_new_technical_metrics %}
    union all

    -- TECHNICAL INDICATORS
    select
        symbol_key,
        trade_date as period_date,
        'daily' as period_type,
        m.metric_code,
        m.metric_value,
        null::timestamp as source_created_at
    from {{ ref('int_technical_indicator') }}
    cross join lateral (
        values
            ('ma_3', ma_3),
            ('ma_5', ma_5),
            ('ma_9', ma_9),
            ('ma_15', ma_15),
            ('ma_20', ma_20),
            ('ma_50', ma_50),
            ('ema_12', ema_12),
            ('ema_26', ema_26),
            ('rsi_14', rsi_14),
            ('macd_line', macd_line),
            ('signal_line', signal_line),
            ('macd_signal', macd_signal),
            ('macd_hist', macd_hist),
            ('bb_upper_20', bb_upper_20),
            ('bb_lower_20', bb_lower_20),
            ('bb_width_20', bb_width_20),
            ('bb_percent_b_20', bb_percent_b_20),
            ('high_10d', high_10d),
            ('atr_14', atr_14),
            ('atr_ma_14', atr_ma_14),
            ('volume', volume),
            ('vol_ma_5', vol_ma_5),
            ('vol_ma_20', vol_ma_20),
            ('vol_ratio_20', vol_ratio_20),
            ('vol_3d_increasing', vol_3d_increasing),
            ('vol_highest_20d', vol_highest_20d),
            ('vol_accumulation', vol_accumulation),
            ('obv', obv),
            ('obv_ma_20', obv_ma_20)
    ) as m(metric_code, metric_value)
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    left join target_max_dates t on t.metric_code = m.metric_code
    {% endif %}
    where m.metric_value is not null
    {% if has_feature_range %}
      and trade_date between '{{ feature_start_date }}'::date and '{{ feature_end_date }}'::date
    {% elif backfill_year is not none %}
      and extract(year from trade_date) = {{ backfill_year }}
    {% elif is_incremental() %}
      and (
          trade_date >= (
              select coalesce(min(t2.max_period_date), '1900-01-01'::date) - interval '40 day'
              from (values
                  ('ma_3'), ('ma_5'), ('ma_9'), ('ma_15'), ('ma_20'), ('ma_50'),
                  ('ema_12'), ('ema_26'), ('rsi_14'),
                  ('macd_line'), ('signal_line'), ('macd_signal'), ('macd_hist'),
                  ('bb_upper_20'), ('bb_lower_20'),
                  ('bb_width_20'), ('bb_percent_b_20'),
                  ('high_10d'), ('atr_14'), ('atr_ma_14'),
                  ('volume'), ('vol_ma_5'), ('vol_ma_20'),
                  ('vol_ratio_20'), ('vol_3d_increasing'),
                  ('vol_highest_20d'), ('vol_accumulation'),
                  ('obv'), ('obv_ma_20')
              ) as v(metric_code)
              left join target_max_dates t2 on v.metric_code = t2.metric_code
          )
          and trade_date >= coalesce(t.max_period_date, '1900-01-01'::date) - interval '40 day'
          {% if backfill_new_technical_metrics %}
          or (
              m.metric_code in (
                  'ma_3'
              )
              and trade_date >= '{{ new_technical_metrics_start_date }}'::date
          )
          {% endif %}
      )
    {% endif %}
    {% endif %}

    {% if not intraday_feature_only %}

    union all

    -- FUNDAMENTALS
    select
        symbol_key,
        period_end_date as period_date,
        'annual' as period_type,
        m.metric_code,
        m.metric_value,
        source_created_at
    from {{ ref('int_fundamental_pivot') }}
    cross join lateral (
        values
            ('total_assets', total_assets),
            ('cash', cash),
            ('total_liabilities', total_liabilities),
            ('equity', equity),
            ('charter_capital', charter_capital),
            ('retained_earnings', retained_earnings),
            ('revenue', revenue),
            ('net_profit', coalesce(net_profit, net_profit_v2)),
            ('profit_before_tax', profit_before_tax),
            ('operating_income', operating_income),
            ('cfo', cfo),
            ('cfi', cfi),
            ('cff', cff),
            ('net_cash_flow', net_cash_flow),
            ('roe', roe),
            ('roa', roa),
            ('eps', eps),
            ('pe', pe),
            ('pb', pb),
            ('bvps', bvps),
            ('net_margin', net_margin),
            ('financial_leverage', financial_leverage),
            ('ps', ps),
            ('p_cash_flow', p_cash_flow_raw),
            ('revenue_growth', revenue_growth),
            ('profit_growth', profit_growth),
            ('customer_loans', customer_loans),
            ('customer_deposits', customer_deposits),
            ('net_interest_income', net_interest_income),
            ('provision_expense', provision_expense),
            ('shares_outstanding', shares_outstanding),
            ('net_asset_value', net_asset_value)
    ) as m(metric_code, metric_value)
    {% if is_incremental() and backfill_year is none and not has_feature_range %}
    left join target_max_dates t on t.metric_code = m.metric_code
    {% endif %}
    where m.metric_value is not null
    {% if has_feature_range %}
      and period_end_date between '{{ feature_start_date }}'::date and '{{ feature_end_date }}'::date
    {% elif backfill_year is not none %}
      and extract(year from period_end_date) = {{ backfill_year }}
    {% elif is_incremental() %}
      {% if has_source_created_at %}
      and source_created_at >= (
          select coalesce(min(t2.max_source_created_at), '1900-01-01'::timestamp) - interval '1 day'
          from (values
              ('total_assets'), ('cash'), ('total_liabilities'), ('equity'),
              ('charter_capital'), ('retained_earnings'), ('revenue'),
              ('net_profit'), ('profit_before_tax'), ('operating_income'),
              ('cfo'), ('cfi'), ('cff'), ('net_cash_flow'),
              ('roe'), ('roa'), ('eps'), ('pe'), ('pb'), ('bvps'),
              ('net_margin'), ('financial_leverage'), ('ps'), ('p_cash_flow'),
              ('revenue_growth'), ('profit_growth'), ('customer_loans'),
              ('customer_deposits'), ('net_interest_income'),
              ('provision_expense'), ('shares_outstanding'), ('net_asset_value')
          ) as v(metric_code)
          left join target_max_dates t2 on v.metric_code = t2.metric_code
      )
      and source_created_at >= coalesce(t.max_source_created_at, '1900-01-01'::timestamp) - interval '1 day'
      {% else %}
      and period_end_date >= (
          select coalesce(min(t2.max_period_date), '1900-01-01'::date) - interval '366 day'
          from (values
              ('total_assets'), ('cash'), ('total_liabilities'), ('equity'),
              ('charter_capital'), ('retained_earnings'), ('revenue'),
              ('net_profit'), ('profit_before_tax'), ('operating_income'),
              ('cfo'), ('cfi'), ('cff'), ('net_cash_flow'),
              ('roe'), ('roa'), ('eps'), ('pe'), ('pb'), ('bvps'),
              ('net_margin'), ('financial_leverage'), ('ps'), ('p_cash_flow'),
              ('revenue_growth'), ('profit_growth'), ('customer_loans'),
              ('customer_deposits'), ('net_interest_income'),
              ('provision_expense'), ('shares_outstanding'), ('net_asset_value')
          ) as v(metric_code)
          left join target_max_dates t2 on v.metric_code = t2.metric_code
      )
      and period_end_date >= coalesce(t.max_period_date, '1900-01-01'::date) - interval '366 day'
      {% endif %}
    {% endif %}

    {% endif %}
)

select
    r.symbol_key,
    r.period_date,
    r.period_type,
    d.metric_key,
    r.metric_code,
    r.metric_value,
    r.source_created_at,
    current_timestamp as created_at
from raw_metrics r
join {{ ref('dim_metric') }} d on r.metric_code = d.metric_code
