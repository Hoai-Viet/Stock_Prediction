-- =====================================================
-- FACT_SCAN - FP-Growth Pattern Scan Results
-- Stores which stocks match high-win-rate patterns
-- =====================================================

CREATE SCHEMA IF NOT EXISTS dwh;

CREATE TABLE IF NOT EXISTS dwh.fact_scan (
    id SERIAL PRIMARY KEY,
    symbol_key INT NOT NULL,
    symbol_code VARCHAR(20) NOT NULL,
    scan_date DATE NOT NULL,
    pattern VARCHAR(255) NOT NULL,
    win_rate NUMERIC(8,5),
    lift NUMERIC(10,5),
    coverage INT,
    model_pred VARCHAR(10),
    fp_signal VARCHAR(10),
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_scan_date
    ON dwh.fact_scan(scan_date);

CREATE INDEX IF NOT EXISTS idx_fact_scan_symbol_date
    ON dwh.fact_scan(symbol_code, scan_date);

CREATE INDEX IF NOT EXISTS idx_fact_scan_confirmed
    ON dwh.fact_scan(is_confirmed, scan_date);

COMMENT ON TABLE dwh.fact_scan IS
    'FP-Growth pattern scan results - stocks matching high-win-rate feature pair patterns';

COMMENT ON COLUMN dwh.fact_scan.is_confirmed IS
    'TRUE if model_pred is BUY or SELL (confirmed by both ML model and FP-Growth pattern)';
