CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS dwh.fact_feature_checkpoint (
    pipeline_name VARCHAR(100) PRIMARY KEY,
    last_processed_date DATE,
    last_successful_run_id VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_fact_feature_checkpoint_status
    ON dwh.fact_feature_checkpoint (status);

CREATE INDEX IF NOT EXISTS idx_fact_feature_checkpoint_updated_at
    ON dwh.fact_feature_checkpoint (updated_at DESC);
