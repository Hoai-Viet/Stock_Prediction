-- =====================================================
-- NEWS SENTIMENT TABLES
-- Raw tables in staging, processed table in dwh
-- =====================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dwh;

-- Raw article storage
CREATE TABLE IF NOT EXISTS staging.fact_news_article (
    article_id BIGSERIAL PRIMARY KEY,
    source_name VARCHAR(30) NOT NULL,
    article_url TEXT NOT NULL,
    article_url_hash VARCHAR(64) NOT NULL,
    title TEXT,
    content_snippet TEXT,
    published_at TIMESTAMPTZ,
    crawl_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    language VARCHAR(10) NOT NULL DEFAULT 'vi',
    sentiment_score NUMERIC(10, 6),
    sentiment_label VARCHAR(10),
    confidence NUMERIC(10, 6),
    quality_flag VARCHAR(20) NOT NULL DEFAULT 'ok',
    UNIQUE (source_name, article_url_hash)
);

CREATE INDEX IF NOT EXISTS idx_news_article_published
    ON staging.fact_news_article (published_at DESC);

CREATE INDEX IF NOT EXISTS idx_news_article_label
    ON staging.fact_news_article (sentiment_label, published_at DESC);

-- Article to symbol mapping
CREATE TABLE IF NOT EXISTS staging.bridge_news_symbol (
    article_id BIGINT NOT NULL REFERENCES staging.fact_news_article(article_id) ON DELETE CASCADE,
    symbol_code VARCHAR(10) NOT NULL,
    match_method VARCHAR(20) NOT NULL DEFAULT 'ticker_regex',
    match_confidence NUMERIC(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, symbol_code)
);

CREATE INDEX IF NOT EXISTS idx_bridge_news_symbol_code
    ON staging.bridge_news_symbol (symbol_code, article_id);

-- Processed daily features
CREATE TABLE IF NOT EXISTS dwh.fact_news_sentiment_daily (
    id BIGSERIAL PRIMARY KEY,
    symbol_key BIGINT,
    period_date DATE NOT NULL,
    period_scope VARCHAR(10) NOT NULL, -- symbol | market
    sentiment_score_t1 NUMERIC(14, 6),
    sentiment_score_t3 NUMERIC(14, 6),
    sentiment_score_t7 NUMERIC(14, 6),
    good_cnt_t1 INT,
    good_cnt_t3 INT,
    good_cnt_t7 INT,
    bad_cnt_t1 INT,
    bad_cnt_t3 INT,
    bad_cnt_t7 INT,
    coverage_t1 INT,
    coverage_t3 INT,
    coverage_t7 INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (symbol_key, period_date, period_scope)
);

CREATE INDEX IF NOT EXISTS idx_fact_news_sentiment_daily_date
    ON dwh.fact_news_sentiment_daily (period_date DESC, period_scope);
