-- =====================================================
-- FACT_FEATURE_PAIR_SIGNAL
-- Stores top feature pairs mined by FP-Growth
-- =====================================================

CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS dwh.fact_feature_pair_signal (
    id SERIAL PRIMARY KEY,
    metric_pair VARCHAR(255) NOT NULL,
    item_a VARCHAR(255) NOT NULL,
    item_b VARCHAR(255) NOT NULL,
    support_count INT NOT NULL,
    coverage_count INT NOT NULL,
    win_count INT NOT NULL,
    win_rate NUMERIC(8,5),
    baseline_win_rate NUMERIC(8,5),
    lift_vs_baseline NUMERIC(10,5),
    predicted_label VARCHAR(10),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feature_pair_signal_pair
    ON dwh.fact_feature_pair_signal(metric_pair);

CREATE INDEX IF NOT EXISTS idx_feature_pair_signal_model
    ON dwh.fact_feature_pair_signal(model_version, predicted_label);

