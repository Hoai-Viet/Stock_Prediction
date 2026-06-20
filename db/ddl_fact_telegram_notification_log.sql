-- =====================================================
-- FACT_TELEGRAM_NOTIFICATION_LOG
-- Tracks successfully sent Telegram notifications
-- =====================================================

CREATE TABLE IF NOT EXISTS dwh.fact_telegram_notification_log (
    id SERIAL PRIMARY KEY,
    recipient_id INT NOT NULL REFERENCES staging.dim_telegram_recipient(recipient_id),
    trade_date DATE NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'ml_decision_signal',
    telegram_message_id VARCHAR(50),
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (recipient_id, trade_date, model_version, notification_type)
);

CREATE INDEX IF NOT EXISTS idx_fact_telegram_notification_log_batch
    ON dwh.fact_telegram_notification_log(trade_date, model_version, notification_type);

COMMENT ON TABLE dwh.fact_telegram_notification_log IS
    'Successfully delivered Telegram notifications for prediction batches';
