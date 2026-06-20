{{ config(materialized='table', schema='dwh') }}

select * from (values
    -- PRICE & RETURN METRICS
    (1,  'close_price',       'price',         'VND',      'Close price', false),
    (2,  'return_1d',         'price',         'percent',  '1-day return', true),
    (70, 'return_3d',         'price',         'percent',  '3-day return', true),
    (71, 'return_next_3d',   'price',         'percent',  'next 3-day return', true),
    (3,  'return_5d',         'price',         'percent',  '5-day return', true),

    -- TECHNICAL INDICATORS
    (81, 'ma_3',              'technical',     'VND',      'SMA 3', true),
    (4,  'ma_5',              'technical',     'VND',      'SMA 5', true),
    (63, 'ma_9',              'technical',     'VND',      'SMA 9', true),
    (64, 'ma_15',             'technical',     'VND',      'SMA 15', true),
    (5,  'ma_20',             'technical',     'VND',      'SMA 20', true),
    (72, 'ma_50',             'technical',     'VND',      'SMA 50', true),
    (6,  'ema_12',            'technical',     'VND',      'EMA 12', true),
    (7,  'ema_26',            'technical',     'VND',      'EMA 26', true),
    (8,  'rsi_14',            'technical',     'index',    'RSI 14', true),
    (9,  'macd_line',         'technical',     'VND',      'MACD line', true),
    (10, 'signal_line',       'technical',     'VND',      'MACD signal line', true),
    (73, 'macd_signal',       'technical',     'VND',      'MACD signal line alias', true),
    (11, 'macd_hist',         'technical',     'VND',      'MACD histogram', true),
    (12, 'bb_upper_20',       'technical',     'VND',      'Bollinger upper (20,2)', true),
    (13, 'bb_lower_20',       'technical',     'VND',      'Bollinger lower (20,2)', true),
    (14, 'bb_width_20',       'technical',     'ratio',    'Bollinger width (20,2)', true),
    (15, 'bb_percent_b_20',   'technical',     'ratio',    'Bollinger %B (20,2)', true),
    (74, 'high_10d',          'technical',     'VND',      'Highest high over previous 10 sessions', true),
    (75, 'atr_14',            'technical',     'VND',      'Average True Range 14', true),
    (76, 'atr_ma_14',         'technical',     'VND',      'Moving average of ATR 14', true),

    -- VOLUME INDICATORS
    (65, 'volume',            'volume',        'shares',   'Daily traded volume', true),
    (66, 'vol_ma_5',          'volume',        'shares',   'Volume moving average 5', true),
    (67, 'vol_ma_20',         'volume',        'shares',   'Volume moving average 20', true),
    (68, 'vol_ratio_20',      'volume',        'ratio',    'Volume / MA20 volume', true),
    (69, 'obv',               'volume',        'shares',   'On-Balance Volume', true),
    (77, 'obv_ma_20',         'volume',        'shares',   'OBV moving average 20', true),
    (78, 'vol_3d_increasing', 'volume',        'flag',     'Volume increases for 3 consecutive sessions', true),
    (79, 'vol_highest_20d',   'volume',        'flag',     'Volume is highest over trailing 20 sessions', true),
    (80, 'vol_accumulation',  'volume',        'flag',     'Low volume base followed by volume expansion', true),

    -- BALANCE SHEET
    (16, 'total_assets',      'balance_sheet', 'VND',      'Total assets', true),
    (17, 'cash',              'balance_sheet', 'VND',      'Cash and equivalents', true),
    (18, 'total_liabilities', 'balance_sheet', 'VND',      'Total liabilities', true),
    (19, 'equity',            'balance_sheet', 'VND',      'Equity', true),
    (20, 'charter_capital',   'balance_sheet', 'VND',      'Charter capital', true),
    (21, 'retained_earnings', 'balance_sheet', 'VND',      'Retained earnings', true),

    -- INCOME STATEMENT
    (22, 'revenue',           'income_stmt',   'VND',      'Revenue', true),
    (23, 'net_profit',        'income_stmt',   'VND',      'Net profit', true),
    (24, 'profit_before_tax', 'income_stmt',   'VND',      'Profit before tax', true),
    (25, 'operating_income',  'income_stmt',   'VND',      'Operating income', true),

    -- CASH FLOW
    (26, 'cfo',               'cash_flow',     'VND',      'Cash flow from operations', true),
    (27, 'cfi',               'cash_flow',     'VND',      'Cash flow from investing', true),
    (28, 'cff',               'cash_flow',     'VND',      'Cash flow from financing', true),
    (29, 'net_cash_flow',     'cash_flow',     'VND',      'Net cash flow', true),

    -- FINANCIAL RATIOS
    (30, 'roe',               'fundamental',   'percent',  'Return on Equity', true),
    (31, 'roa',               'fundamental',   'percent',  'Return on Assets', true),
    (32, 'eps',               'fundamental',   'VND',      'Earnings per Share', true),
    (33, 'pe',                'fundamental',   'ratio',    'Price to Earnings', true),
    (34, 'pb',                'fundamental',   'ratio',    'Price to Book', true),
    (35, 'bvps',              'fundamental',   'VND',      'Book Value per Share', true),
    (36, 'net_margin',        'fundamental',   'percent',  'Net margin', true),
    (37, 'financial_leverage','fundamental',   'ratio',    'Financial leverage', true),
    (38, 'ps',                'fundamental',   'ratio',    'Price to Sales', true),
    (39, 'p_cash_flow',       'fundamental',   'ratio',    'Price to Cash Flow', true),
    (40, 'revenue_growth',    'fundamental',   'percent',  'Revenue growth', true),
    (41, 'profit_growth',     'fundamental',   'percent',  'Profit growth', true),

    -- BANKING SPECIFIC
    (42, 'customer_loans',      'banking',     'VND',      'Customer loans', true),
    (43, 'customer_deposits',   'banking',     'VND',      'Customer deposits', true),
    (44, 'net_interest_income', 'banking',     'VND',      'Net interest income', true),
    (45, 'provision_expense',   'banking',     'VND',      'Provision expense', true),
    (46, 'shares_outstanding',  'fundamental', 'M shares', 'Shares outstanding', true),
    (47, 'net_asset_value',     'fundamental', 'VND',      'Net asset value', true),

    -- NEWS SENTIMENT (SYMBOL LEVEL)
    (48, 'news_sent_score_t1',  'news',        'score',    'News sentiment score (T-1)', true),
    (49, 'news_sent_score_t3',  'news',        'score',    'News sentiment score (T-3)', true),
    (50, 'news_sent_score_t7',  'news',        'score',    'News sentiment score (T-7)', true),
    (51, 'news_good_cnt_t1',    'news',        'count',    'Good news count (T-1)', true),
    (52, 'news_good_cnt_t3',    'news',        'count',    'Good news count (T-3)', true),
    (53, 'news_good_cnt_t7',    'news',        'count',    'Good news count (T-7)', true),
    (54, 'news_bad_cnt_t1',     'news',        'count',    'Bad news count (T-1)', true),
    (55, 'news_bad_cnt_t3',     'news',        'count',    'Bad news count (T-3)', true),
    (56, 'news_bad_cnt_t7',     'news',        'count',    'Bad news count (T-7)', true),
    (57, 'news_coverage_t1',    'news',        'count',    'Mapped news coverage (T-1)', true),
    (58, 'news_coverage_t3',    'news',        'count',    'Mapped news coverage (T-3)', true),
    (59, 'news_coverage_t7',    'news',        'count',    'Mapped news coverage (T-7)', true),

    -- NEWS SENTIMENT (MARKET LEVEL)
    (60, 'mkt_news_sent_score_t1', 'news_market', 'score', 'Market news sentiment score (T-1)', true),
    (61, 'mkt_news_sent_score_t3', 'news_market', 'score', 'Market news sentiment score (T-3)', true),
    (62, 'mkt_news_sent_score_t7', 'news_market', 'score', 'Market news sentiment score (T-7)', true)

) as t(metric_key, metric_code, metric_group, unit, description, is_ml_feature)



