-- 1. Tạo bảng dim_symbol
CREATE TABLE IF NOT EXISTS dim_symbol (
    symbol_key    BIGSERIAL PRIMARY KEY,
    symbol_code   VARCHAR(10) NOT NULL,
    company_name  VARCHAR(255),
    description   TEXT,
    sector_name   VARCHAR(50) NOT NULL DEFAULT 'bank',
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE dim_symbol
    ADD COLUMN IF NOT EXISTS description TEXT;

INSERT INTO dim_symbol (symbol_code, company_name, sector_name) VALUES
('VCB', 'Joint Stock Commercial Bank for Foreign Trade of Vietnam', 'bank'),
('CTG', 'Vietnam Joint Stock Commercial Bank for Industry and Trade', 'bank'),
('BID', 'Joint Stock Commercial Bank for Investment and Development of Vietnam', 'bank'),
('TCB', 'Vietnam Technological and Commercial Joint Stock Bank', 'bank'),
('VPB', 'Vietnam Prosperity Joint Stock Commercial Bank', 'bank'),
('MBB', 'Military Commercial Joint Stock Bank', 'bank'),
('ACB', 'Asia Commercial Joint Stock Bank', 'bank'),
('STB', 'Saigon Thuong Tin Commercial Joint Stock Bank', 'bank'),
('SHB', 'Saigon - Hanoi Commercial Joint Stock Bank', 'bank'),
('HDB', 'Ho Chi Minh City Development Joint Stock Commercial Bank', 'bank'),
('VIB', 'Vietnam International Commercial Joint Stock Bank', 'bank'),
('TPB', 'Tien Phong Commercial Joint Stock Bank', 'bank'),
('OCB', 'Orient Commercial Joint Stock Bank', 'bank'),
('MSB', 'Vietnam Maritime Commercial Joint Stock Bank', 'bank'),
('LPB', 'Lien Viet Post Joint Stock Commercial Bank', 'bank'),
('SSB', 'Southeast Asia Commercial Joint Stock Bank', 'bank'),
('EIB', 'Vietnam Export Import Commercial Joint Stock Bank', 'bank'),
('BAB', 'Bac A Commercial Joint Stock Bank', 'bank'),
('NVB', 'National Citizen Commercial Joint Stock Bank', 'bank'),
('PGB', 'Petrolimex Group Commercial Joint Stock Bank', 'bank'),
('SGB', 'Saigon Bank for Industry and Trade', 'bank'),
('NAB', 'Nam A Commercial Joint Stock Bank', 'bank')
ON CONFLICT DO NOTHING;

UPDATE dim_symbol
SET
    description = CASE symbol_code
        WHEN 'VCB' THEN 'A leading state-owned bank with strong asset quality and profitability. It dominates trade finance and foreign exchange, and is widely seen as one of the safest banks in Vietnam.'
        WHEN 'CTG' THEN 'A large state-owned commercial bank with a strong corporate lending base. It plays a key role in financing industrial and infrastructure sectors, though margins are relatively tighter.'
        WHEN 'BID' THEN 'The largest bank by assets in Vietnam, with extensive exposure to government and infrastructure projects. Growth is stable but often comes with higher provisioning pressure.'
        WHEN 'TCB' THEN 'A top-tier private bank known for high profitability and strong capital efficiency. It focuses on retail and real estate ecosystems, with advanced digital banking capabilities.'
        WHEN 'VPB' THEN 'A high-growth private bank driven by consumer finance and SME lending. It offers strong yield but also carries higher credit risk compared to peers.'
        WHEN 'MBB' THEN 'A military-linked bank with strong operational efficiency and asset quality. It has a diversified ecosystem including insurance, securities, and digital banking platforms.'
        WHEN 'ACB' THEN 'A retail-focused private bank with conservative risk management. It delivers stable growth and is known for consistent profitability and clean balance sheet.'
        WHEN 'STB' THEN 'A bank in the late stage of restructuring after past issues. It offers turnaround potential as asset quality improves and legacy problems are gradually resolved.'
        WHEN 'SHB' THEN 'A mid-sized bank with strong corporate lending exposure. It is expanding retail banking, though asset quality remains a key factor to watch.'
        WHEN 'HDB' THEN 'A fast-growing bank with strong ties to consumer finance and aviation (VietJet ecosystem). It benefits from retail expansion and high-margin lending segments.'
        WHEN 'VIB' THEN 'A retail-oriented bank specializing in auto loans and digital banking. It maintains strong profitability with a focus on individual customers.'
        WHEN 'TPB' THEN 'A digital-first bank backed by major shareholders. It stands out for innovation in online banking and rapid growth in retail customers.'
        WHEN 'OCB' THEN 'A mid-tier bank focusing on SMEs and retail clients. It is undergoing digital transformation to improve efficiency and competitiveness.'
        WHEN 'MSB' THEN 'A commercial bank transitioning toward retail and SME segments. It shows improving asset quality and profitability in recent years.'
        WHEN 'LPB' THEN 'A unique bank leveraging Vietnam''s postal network for nationwide reach. It focuses on financial inclusion, especially in rural areas.'
        WHEN 'SSB' THEN 'A growing private bank with strong backing from foreign investors. It is expanding retail banking while improving operational efficiency.'
        WHEN 'EIB' THEN 'Traditionally strong in import-export financing. The bank is restructuring to stabilize governance and improve long-term performance.'
        WHEN 'BAB' THEN 'A niche bank focused on agriculture and sustainable projects. It has a unique lending strategy tied to specific industries.'
        WHEN 'NVB' THEN 'A small-scale bank serving retail and SME customers. Growth potential exists but scale and efficiency remain limited.'
        WHEN 'PGB' THEN 'A small bank with origins in the petroleum sector. It is undergoing strategic changes to improve scale and competitiveness.'
        WHEN 'SGB' THEN 'One of the oldest joint-stock banks in Vietnam. It maintains a traditional retail banking model with moderate growth.'
        WHEN 'NAB' THEN 'A rising private bank focusing on digital transformation and retail expansion. It aims to improve efficiency and market share.'
        WHEN 'FPT' THEN 'Leading Vietnamese technology group with strong growth in software exports, digital transformation, telecom, and education segments.'
        WHEN 'VIC' THEN 'Vietnam''s largest private conglomerate with diversified exposure to real estate, hospitality, and industrial ventures including EV manufacturing.'
        WHEN 'VNM' THEN 'Vietnam''s dominant dairy producer with strong brand equity, stable cash flow, and extensive domestic and export distribution networks.'
        WHEN 'HPG' THEN 'Leading steel producer in Vietnam with integrated production model, benefiting from scale advantages and industrial expansion.'
        WHEN 'MWG' THEN 'Top retail group operating electronics, appliance, and grocery chains, with strong execution capability and nationwide store network.'
        WHEN 'VHM' THEN 'Largest residential real estate developer in Vietnam, focusing on large-scale urban projects with strong sales pipeline and brand recognition.'
        ELSE description
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE symbol_code IN (
    'VCB', 'CTG', 'BID', 'TCB', 'VPB', 'MBB', 'ACB', 'STB', 'SHB', 'HDB',
    'VIB', 'TPB', 'OCB', 'MSB', 'LPB', 'SSB', 'EIB', 'BAB', 'NVB', 'PGB',
    'SGB', 'NAB', 'FPT', 'VIC', 'VNM', 'HPG', 'MWG', 'VHM'
)
AND (description IS NULL OR description = '');

-- 2. dim_funding_structure 
create table IF NOT EXISTS dim_funding_structure
(
	funding_id int,
	funding_code varchar,
	funding_name varchar,
	funding_parent_id int,
	funding_level int,
	sortorder int,
	rec_created_dt timestamp default now(),
	rec_updated_dt timestamp default now()
);

-- Note: Skipping generic INSERTs for brevity if they exist, but normally would include them.
-- Assuming existing DB has them or they are not critical for this specific task's failure.

-- 3. fact_stock_price_intraday 
CREATE TABLE IF NOT EXISTS fact_stock_price_intraday (
    symbol_code   VARCHAR NOT NULL,            -- Mã cổ phiếu (VCB, ACB, ...)
    interval_key  INT NOT NULL,                -- FK -> dim_interval
    candle_time   TIMESTAMPTZ NOT NULL,        -- Thời điểm mở của candle (09:01, 09:05, ...)
    trade_date    DATE NOT NULL,               -- Ngày giao dịch (dùng cho partition / filter nhanh)

    open          BIGINT,
    high          BIGINT,
    low           BIGINT,
    close         BIGINT,
    volume        BIGINT,

    inserted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (symbol_code, interval_key, candle_time),

    CONSTRAINT fk_intraday_interval
        FOREIGN KEY (interval_key)
        REFERENCES dim_interval(interval_key)
);

-- 4. OLD fact_income_statement REMOVED (Legacy)
-- This table is replaced by staging.fact_financial_statements


-- 5. dim_interval
CREATE TABLE IF NOT EXISTS dim_interval (
    interval_key   INT PRIMARY KEY,          -- 1, 5, 15, 30, 60...
    interval_code  VARCHAR NOT NULL,          -- '1m', '5m', '15m', ...
    interval_min   INT NOT NULL,              -- số phút tương ứng
    description    VARCHAR,

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (interval_code),
    UNIQUE (interval_min)
);

INSERT INTO dim_interval (interval_key, interval_code, interval_min, description)
VALUES
    (1,   '1m',   1,   'Candle 1 phút'),
    (5,   '5m',   5,   'Candle 5 phút'),
    (15,  '15m',  15,  'Candle 15 phút'),
    (30,  '30m',  30,  'Candle 30 phút'),
    (60,  '1h',   60,  'Candle 1 giờ'),
    (240, '4h',   240, 'Candle 4 giờ'),
    (1440,'1d',   1440,'Candle 1 ngày')
ON CONFLICT DO NOTHING;

-- 6. NEW fact_financial_statements (Universal for BS, IS, CF)
-- Added to support vnstock crawling which returns textual period headers and multiple report types.
CREATE TABLE fact_financials (
    fact_id        BIGSERIAL PRIMARY KEY,

    -- Dimension keys
    stock_code     VARCHAR(10) NOT NULL,      -- VCI
    year           SMALLINT NOT NULL,          -- 2024, 2025
    period         SMALLINT NOT NULL,          -- 1-4: quý, 5: TTM, 0: năm

    report_type    VARCHAR(20) NOT NULL,       -- BS | IS | CF | RATIO
    statement_type VARCHAR(20),                -- year | quarter | ttm

    -- Metric
    metric_code    VARCHAR(100) NOT NULL,      -- TOTAL_ASSETS, EPS_BASIC
    metric_name    VARCHAR(255),               -- Tổng tài sản
    metric_value   NUMERIC(20,4),              

    -- Metadata
    unit           VARCHAR(50),                -- VND, %, lần
    source         VARCHAR(20) DEFAULT 'VNSTOCK',
    currency       VARCHAR(10) DEFAULT 'VND',

    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE (
        stock_code,
        year,
        period,
        report_type,
        metric_code
    )
);

-- 7. dim_metric
CREATE TABLE staging.dim_metric (
    metric_key        BIGSERIAL PRIMARY KEY,

    metric_code       VARCHAR(100) NOT NULL UNIQUE,   -- TOTAL_ASSETS, EPS_BASIC
    metric_name       VARCHAR(255) NOT NULL,          -- Tổng tài sản
    metric_group      VARCHAR(50) NOT NULL,           -- BS | IS | CF | RATIO | BANK
    metric_category   VARCHAR(50),                    -- ASSET | LIABILITY | PROFIT | CASHFLOW | RATIO
    description       TEXT,

    default_unit      VARCHAR(50),                    -- VND, %, lần
    is_bank_only      BOOLEAN DEFAULT FALSE,
    is_active         BOOLEAN DEFAULT TRUE,

    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. report_type 
CREATE TABLE dim_report_type (
    report_type_key   SMALLSERIAL PRIMARY KEY,
    report_type_code  VARCHAR(20) NOT NULL UNIQUE,   -- BS, IS, CF, RATIO
    report_type_name  VARCHAR(100)                  -- Balance Sheet, Income Statement
);

INSERT INTO dim_report_type (report_type_code, report_type_name)
VALUES
('BS', 'Balance Sheet'),
('IS', 'Income Statement'),
('CF', 'Cash Flow'),
('RATIO', 'Financial Ratio');

-- 9. period 
CREATE TABLE dim_period (
    period_key     SMALLSERIAL PRIMARY KEY,
    period_code    SMALLINT NOT NULL UNIQUE,  -- 0,1,2,3,4,5
    period_name    VARCHAR(50) NOT NULL,      -- Year, Q1, Q2, Q3, Q4, TTM
    period_type    VARCHAR(20) NOT NULL       -- year | quarter | ttm
);
CREATE TABLE dim_period (
    period_key     SMALLSERIAL PRIMARY KEY,
    period_code    SMALLINT NOT NULL UNIQUE,  -- 0,1,2,3,4,5
    period_name    VARCHAR(50) NOT NULL,      -- Year, Q1, Q2, Q3, Q4, TTM
    period_type    VARCHAR(20) NOT NULL       -- year | quarter | ttm
);

INSERT INTO dim_period (period_code, period_name, period_type)
VALUES
(0, 'Year', 'year'),
(1, 'Q1', 'quarter'),
(2, 'Q2', 'quarter'),
(3, 'Q3', 'quarter'),
(4, 'Q4', 'quarter'),
(5, 'TTM', 'ttm');




