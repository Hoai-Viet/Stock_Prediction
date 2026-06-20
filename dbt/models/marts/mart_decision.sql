{{ config(materialized='view') }}

-- mart_decision: Expose ML predictions for reporting
-- Source: dwh.fact_decision (populated by ml/predict.py)
-- Includes entry timing data. Evaluation data is now part of fact_decision but not yet populated in DDL, so we select what exists.

SELECT
    d.id,
    d.symbol_key,
    d.trade_date,
    
    -- Decision prediction
    d.predicted_label,
    -- Probabilities removed as requested
    
    -- Entry timing
    d.entry_window,
    d.entry_time_from,
    d.entry_time_to,
    
    -- Metadata
    d.model_version,
    d.timing_model_version,
    d.generated_at,
    
    -- Evaluation (available fields from fact_decision)
    d.actual_direction as actual_label,
    d.is_correct,
    d.evaluated_at,
    
    -- Status flag
    CASE WHEN d.evaluated_at IS NOT NULL THEN TRUE ELSE FALSE END AS is_evaluated
    
FROM {{ source('dwh', 'fact_decision') }} d
