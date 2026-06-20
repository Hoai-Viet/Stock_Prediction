-- =====================================================
-- DIM_TELEGRAM_RECIPIENT
-- Stores Telegram recipients for stock notifications
-- =====================================================

CREATE TABLE IF NOT EXISTS staging.dim_telegram_recipient (
    recipient_id SERIAL PRIMARY KEY,
    recipient_name VARCHAR(255),
    chat_id VARCHAR(50) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE staging.dim_telegram_recipient IS
    'List of Telegram recipients that receive stock signal notifications';

COMMENT ON COLUMN staging.dim_telegram_recipient.chat_id IS
    'Telegram chat identifier for a user, group, or channel';
