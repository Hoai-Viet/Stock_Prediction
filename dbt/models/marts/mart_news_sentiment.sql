{{ config(materialized='view') }}

SELECT
    id,
    symbol_key,
    period_date AS trade_date,
    period_scope,
    sentiment_score_t1,
    sentiment_score_t3,
    sentiment_score_t7,
    good_cnt_t1,
    good_cnt_t3,
    good_cnt_t7,
    bad_cnt_t1,
    bad_cnt_t3,
    bad_cnt_t7,
    coverage_t1,
    coverage_t3,
    coverage_t7,
    created_at,
    updated_at
FROM {{ source('dwh', 'fact_news_sentiment_daily') }}
