-- =====================================================
-- NEWS KEYWORD & SYMBOL ALIAS TABLES
-- Replaces hardcoded POSITIVE_TERMS, NEGATIVE_TERMS,
-- and SYMBOL_ALIASES in crawl_news.py
-- =====================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- Sentiment keywords (positive & negative)
CREATE TABLE IF NOT EXISTS staging.dim_news_keyword (
    keyword_id SERIAL PRIMARY KEY,
    term VARCHAR(100) NOT NULL,
    sentiment VARCHAR(10) NOT NULL CHECK (sentiment IN ('positive', 'negative')),
    weight NUMERIC(6, 4) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (term)
);

CREATE INDEX IF NOT EXISTS idx_dim_news_keyword_active
    ON staging.dim_news_keyword (is_active, sentiment);

-- Symbol alias mapping
CREATE TABLE IF NOT EXISTS staging.dim_symbol_alias (
    alias_id SERIAL PRIMARY KEY,
    symbol_code VARCHAR(10) NOT NULL,
    alias VARCHAR(200) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (symbol_code, alias)
);

CREATE INDEX IF NOT EXISTS idx_dim_symbol_alias_active
    ON staging.dim_symbol_alias (is_active, symbol_code);


-- =====================================================
-- SEED DATA: Positive keywords
-- =====================================================
INSERT INTO staging.dim_news_keyword (term, sentiment, weight) VALUES
    ('tang truong',              'positive',  0.35),
    ('loi nhuan tang',           'positive',  0.40),
    ('vuot ke hoach',            'positive',  0.35),
    ('chia co tuc',              'positive',  0.25),
    ('mua lai co phieu',         'positive',  0.25),
    ('nang hang',                'positive',  0.30),
    ('ky hop dong',              'positive',  0.20),
    ('ban le tang',              'positive',  0.20),
    ('vuot dinh',                'positive',  0.20),
    ('duoc chap thuan',          'positive',  0.20),
    ('mua rong',                 'positive',  0.15),
    ('ket qua kinh doanh tot',  'positive',  0.30)
ON CONFLICT (term) DO NOTHING;

-- =====================================================
-- SEED DATA: Negative keywords
-- =====================================================
INSERT INTO staging.dim_news_keyword (term, sentiment, weight) VALUES
    ('sut giam',     'negative', -0.35),
    ('lo rong',      'negative', -0.45),
    ('bi xu phat',   'negative', -0.45),
    ('dieu tra',     'negative', -0.40),
    ('no xau tang',  'negative', -0.40),
    ('ha trien vong','negative', -0.35),
    ('thua lo',      'negative', -0.45),
    ('giam manh',    'negative', -0.35),
    ('ap luc ban',   'negative', -0.20),
    ('bi canh bao',  'negative', -0.30),
    ('cat giam',     'negative', -0.25),
    ('rut rong',     'negative', -0.15)
ON CONFLICT (term) DO NOTHING;

-- =====================================================
-- SEED DATA: Symbol aliases
-- =====================================================
INSERT INTO staging.dim_symbol_alias (symbol_code, alias) VALUES
    ('VCB', 'vietcombank'),
    ('VCB', 'ngoai thuong'),
    ('CTG', 'vietinbank'),
    ('CTG', 'cong thuong'),
    ('BID', 'bidv'),
    ('BID', 'dau tu va phat trien'),
    ('TCB', 'techcombank'),
    ('VPB', 'vpbank'),
    ('MBB', 'mbbank'),
    ('MBB', 'quan doi'),
    ('ACB', 'asia commercial bank'),
    ('STB', 'sacombank'),
    ('SHB', 'saigon hanoi bank'),
    ('HDB', 'hdbank'),
    ('VIB', 'vib bank'),
    ('VIB', 'vietnam international bank'),
    ('TPB', 'tpbank'),
    ('TPB', 'tien phong bank'),
    ('OCB', 'orient commercial bank'),
    ('MSB', 'maritime bank'),
    ('MSB', 'msb bank'),
    ('LPB', 'lienvietpostbank'),
    ('LPB', 'loc phat bank'),
    ('SSB', 'seabank'),
    ('EIB', 'eximbank'),
    ('BAB', 'bac a bank'),
    ('NVB', 'nvb bank'),
    ('NVB', 'quoc dan bank'),
    ('PGB', 'pg bank'),
    ('PGB', 'petrolimex bank'),
    ('SGB', 'saigonbank'),
    ('NAB', 'nam a bank')
ON CONFLICT (symbol_code, alias) DO NOTHING;
