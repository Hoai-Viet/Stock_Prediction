-- Bảng log trạng thái mỗi lần crawl BCTC
CREATE TABLE IF NOT EXISTS staging.crawl_log (
    log_id        BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL,                -- UUID unique cho mỗi lần chạy crawl
    stock_code    VARCHAR(10) NOT NULL,
    report_type   VARCHAR(20),                  -- BS, IS, CF, RATIO hoặc NULL nếu failed toàn bộ
    source        VARCHAR(20),                  -- VCI, TCBS, VNDIRECT
    status        VARCHAR(20) NOT NULL,         -- SUCCESS, FAILED, PARTIAL, RETRY_SUCCESS
    rows_inserted INT DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index để query nhanh theo run_id và status
CREATE INDEX IF NOT EXISTS idx_crawl_log_run_id ON staging.crawl_log (run_id);
CREATE INDEX IF NOT EXISTS idx_crawl_log_status ON staging.crawl_log (status);
CREATE INDEX IF NOT EXISTS idx_crawl_log_created_at ON staging.crawl_log (created_at DESC);
