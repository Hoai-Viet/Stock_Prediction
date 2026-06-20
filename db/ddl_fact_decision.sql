-- =====================================================
-- FACT_DECISION - ML Model Predictions
-- Stores BUY/SELL/SILENT recommendations per stock per day
-- with entry timing suggestions
-- =====================================================

-- Ensure dwh schema exists
CREATE SCHEMA IF NOT EXISTS dwh;

-- Create fact_decision table
DROP TABLE IF EXISTS dwh.fact_decision CASCADE;

CREATE TABLE dwh.fact_decision (
    id SERIAL PRIMARY KEY,
    symbol_key INT NOT NULL,
    trade_date DATE NOT NULL,
    
    -- Prediction vs Actual (side by side for easy comparison)
    predicted_label VARCHAR(10) NOT NULL CHECK (predicted_label IN ('BUY', 'SELL', 'SILENT')),
    actual_direction VARCHAR(10) CHECK (actual_direction IN ('BUY', 'SELL', 'SILENT')),
    is_correct BOOLEAN,               -- TRUE if prediction matched actual direction
    evaluated_at TIMESTAMP,           -- When actual was calculated
    
    -- Entry Timing (Intraday)
    entry_window VARCHAR(20) CHECK (entry_window IN ('OPEN', 'MORNING', 'AFTERNOON', 'CLOSE', 'NONE')),
    entry_time_from TIME,         -- Start of recommended entry window
    entry_time_to TIME,           -- End of recommended entry window
    
    -- Metadata
    model_version VARCHAR(50) NOT NULL,      -- e.g., 'v1.0_20260205'
    timing_model_version VARCHAR(50),        -- Version of entry timing model (if separate)
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: one prediction per symbol per date per model version
    UNIQUE (symbol_key, trade_date, model_version)
);

-- Indexes for common query patterns
CREATE INDEX idx_fact_decision_trade_date 
    ON dwh.fact_decision(trade_date);

CREATE INDEX idx_fact_decision_symbol_date 
    ON dwh.fact_decision(symbol_key, trade_date);

CREATE INDEX idx_fact_decision_label 
    ON dwh.fact_decision(predicted_label, trade_date);

CREATE INDEX idx_fact_decision_entry_window 
    ON dwh.fact_decision(entry_window, trade_date);

-- Comments
COMMENT ON TABLE dwh.fact_decision IS 
    'ML model predictions for stock trading decisions (BUY/SELL/SILENT) with intraday entry timing';

COMMENT ON COLUMN dwh.fact_decision.predicted_label IS 
    'Model prediction: BUY (future_return >= 2%), SELL (future_return <= -2%), SILENT (otherwise)';

COMMENT ON COLUMN dwh.fact_decision.is_correct IS 
    'TRUE if predicted direction matched actual direction';

COMMENT ON COLUMN dwh.fact_decision.entry_window IS 
    'Recommended entry window: OPEN (9:00-9:45), MORNING (9:45-11:30), AFTERNOON (13:00-14:15), CLOSE (14:15-14:45)';

COMMENT ON COLUMN dwh.fact_decision.model_version IS 
    'Version identifier for the decision model that generated this prediction';

COMMENT ON COLUMN dwh.fact_decision.timing_model_version IS 
    'Version identifier for the entry timing model (NULL if same as model_version or not using separate model)';
