-- =====================================================
-- DIM_METRIC - Danh sách các chỉ tiêu tài chính
-- Cập nhật để khớp với metric codes từ BCTC (dim_funding_structure)
-- source: MANUAL = tự thêm, BS/IS/CF/RATIO = từ báo cáo tài chính
-- =====================================================
-- Tạo schema nếu chưa có
CREATE SCHEMA IF NOT EXISTS dwh;
-- Drop và tạo lại bảng
DROP TABLE IF EXISTS dwh.dim_metric;
CREATE TABLE dwh.dim_metric (
    metric_id SERIAL PRIMARY KEY,
    metric_code VARCHAR(100) UNIQUE NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    sub_category VARCHAR(100),
    formula_description TEXT,
    source VARCHAR(20) DEFAULT 'MANUAL' -- MANUAL, BS, IS, CF, RATIO
);
INSERT INTO dwh.dim_metric (
        metric_code,
        metric_name,
        category,
        sub_category,
        formula_description,
        source
    )
VALUES -- =====================================================
    -- TECHNICAL INDICATORS (Chỉ số kỹ thuật) - MANUAL
    -- =====================================================
    (
        'MA',
        'Moving Average',
        'Technical',
        'Trend',
        '(d1 + d2 + d3 + … + dn) / n',
        'MANUAL'
    ),
    (
        'RSI',
        'Relative Strength Index',
        'Technical',
        'Momentum',
        '100 – (100 / (1 + RS))',
        'MANUAL'
    ),
    (
        'MACD',
        'Moving Average Convergence Divergence',
        'Technical',
        'Momentum',
        'EMA (C, 12) – EMA (C, 26)',
        'MANUAL'
    ),
    (
        'BOLLINGER_BANDS',
        'Bollinger Bands',
        'Technical',
        'Volatility',
        'MA +/- 2 σ',
        'MANUAL'
    ),
    -- =====================================================
    -- BALANCE SHEET - Bảng cân đối kế toán (source = BS)
    -- =====================================================
    (
        'TỔNG_TÀI_SẢN',
        'Tổng tài sản',
        'Financial',
        'Balance Sheet',
        'Tổng giá trị tài sản của doanh nghiệp',
        'BS'
    ),
    (
        'TÀI_SẢN_NGẮN_HẠN',
        'Tài sản ngắn hạn',
        'Financial',
        'Balance Sheet',
        'Current assets',
        'BS'
    ),
    (
        'TÀI_SẢN_DÀI_HẠN',
        'Tài sản dài hạn',
        'Financial',
        'Balance Sheet',
        'Non-current assets',
        'BS'
    ),
    (
        'TIỀN_VÀ_CÁC_KHOẢN_TƯƠNG_ĐƯƠNG_TIỀN',
        'Tiền và các khoản tương đương tiền',
        'Financial',
        'Balance Sheet',
        'Cash and cash equivalents',
        'BS'
    ),
    (
        'CÁC_KHOẢN_ĐẦU_TƯ_TÀI_CHÍNH_NGẮN_HẠN',
        'Các khoản đầu tư tài chính ngắn hạn',
        'Financial',
        'Balance Sheet',
        'Short-term investments',
        'BS'
    ),
    (
        'CÁC_KHOẢN_PHẢI_THU_NGẮN_HẠN',
        'Các khoản phải thu ngắn hạn',
        'Financial',
        'Balance Sheet',
        'Short-term receivables',
        'BS'
    ),
    (
        'HÀNG_TỒN_KHO',
        'Hàng tồn kho',
        'Financial',
        'Balance Sheet',
        'Inventories',
        'BS'
    ),
    (
        'TỔNG_NGUỒN_VỐN',
        'Tổng nguồn vốn',
        'Financial',
        'Balance Sheet',
        'Total liabilities and equity',
        'BS'
    ),
    (
        'NỢ_PHẢI_TRẢ',
        'Nợ phải trả',
        'Financial',
        'Balance Sheet',
        'Total liabilities',
        'BS'
    ),
    (
        'NỢ_NGẮN_HẠN',
        'Nợ ngắn hạn',
        'Financial',
        'Balance Sheet',
        'Current liabilities',
        'BS'
    ),
    (
        'NỢ_DÀI_HẠN',
        'Nợ dài hạn',
        'Financial',
        'Balance Sheet',
        'Non-current liabilities',
        'BS'
    ),
    (
        'VỐN_CHỦ_SỞ_HỮU',
        'Vốn chủ sở hữu',
        'Financial',
        'Balance Sheet',
        'Total equity',
        'BS'
    ),
    (
        'VỐN_ĐIỀU_LỆ',
        'Vốn điều lệ',
        'Financial',
        'Balance Sheet',
        'Charter capital',
        'BS'
    ),
    (
        'LỢI_NHUẬN_CHƯA_PHÂN_PHỐI',
        'Lợi nhuận chưa phân phối',
        'Financial',
        'Balance Sheet',
        'Retained earnings',
        'BS'
    ),
    -- =====================================================
    -- INCOME STATEMENT - Báo cáo kết quả kinh doanh (source = IS)
    -- =====================================================
    (
        'DOANH_THU_THUẦN',
        'Doanh thu thuần',
        'Financial',
        'Income Statement',
        'Net revenue',
        'IS'
    ),
    (
        'GIÁ_VỐN_HÀNG_BÁN',
        'Giá vốn hàng bán',
        'Financial',
        'Income Statement',
        'Cost of goods sold',
        'IS'
    ),
    (
        'LỢI_NHUẬN_GỘP',
        'Lợi nhuận gộp',
        'Financial',
        'Income Statement',
        'Gross profit',
        'IS'
    ),
    (
        'CHI_PHÍ_TÀI_CHÍNH',
        'Chi phí tài chính',
        'Financial',
        'Income Statement',
        'Financial expenses',
        'IS'
    ),
    (
        'CHI_PHÍ_BÁN_HÀNG',
        'Chi phí bán hàng',
        'Financial',
        'Income Statement',
        'Selling expenses',
        'IS'
    ),
    (
        'CHI_PHÍ_QUẢN_LÝ_DOANH_NGHIỆP',
        'Chi phí quản lý doanh nghiệp',
        'Financial',
        'Income Statement',
        'General & admin expenses',
        'IS'
    ),
    (
        'LỢI_NHUẬN_THUẦN_TỪ_HOẠT_ĐỘNG_KINH_DOANH',
        'Lợi nhuận thuần từ hoạt động kinh doanh',
        'Financial',
        'Income Statement',
        'Operating profit',
        'IS'
    ),
    (
        'LỢI_NHUẬN_TRƯỚC_THUẾ',
        'Lợi nhuận trước thuế',
        'Financial',
        'Income Statement',
        'Profit before tax',
        'IS'
    ),
    (
        'LỢI_NHUẬN_SAU_THUẾ',
        'Lợi nhuận sau thuế',
        'Financial',
        'Income Statement',
        'Net profit after tax',
        'IS'
    ),
    -- =====================================================
    -- CASH FLOW - Báo cáo lưu chuyển tiền tệ (source = CF)
    -- =====================================================
    (
        'LƯU_CHUYỂN_TIỀN_TỪ_HOẠT_ĐỘNG_KINH_DOANH',
        'Lưu chuyển tiền từ hoạt động kinh doanh',
        'Financial',
        'Cash Flow',
        'CFO - Operating cash flow',
        'CF'
    ),
    (
        'LƯU_CHUYỂN_TIỀN_TỪ_HOẠT_ĐỘNG_ĐẦU_TƯ',
        'Lưu chuyển tiền từ hoạt động đầu tư',
        'Financial',
        'Cash Flow',
        'CFI - Investing cash flow',
        'CF'
    ),
    (
        'LƯU_CHUYỂN_TIỀN_TỪ_HOẠT_ĐỘNG_TÀI_CHÍNH',
        'Lưu chuyển tiền từ hoạt động tài chính',
        'Financial',
        'Cash Flow',
        'CFF - Financing cash flow',
        'CF'
    ),
    (
        'TIỀN_THUẦN_TRONG_KỲ',
        'Tiền thuần trong kỳ',
        'Financial',
        'Cash Flow',
        'Net cash flow',
        'CF'
    ),
    -- =====================================================
    -- FINANCIAL RATIOS - Các chỉ số tài chính (source = RATIO)
    -- =====================================================
    -- Profitability
    (
        'ROE_(_)',
        'ROE (%)',
        'Financial',
        'Profitability',
        'Return on Equity = Lợi nhuận sau thuế / Vốn chủ sở hữu bình quân',
        'RATIO'
    ),
    (
        'ROA_(_)',
        'ROA (%)',
        'Financial',
        'Profitability',
        'Return on Assets = Lợi nhuận sau thuế / Tổng tài sản bình quân',
        'RATIO'
    ),
    (
        'ROIC_(_)',
        'ROIC (%)',
        'Financial',
        'Profitability',
        'Return on Invested Capital',
        'RATIO'
    ),
    (
        'BIÊN_LỢI_NHUẬN_GỘP_(_)',
        'Biên lợi nhuận gộp (%)',
        'Financial',
        'Profitability',
        'Gross profit margin',
        'RATIO'
    ),
    (
        'BIÊN_LỢI_NHUẬN_RÒNG_(_)',
        'Biên lợi nhuận ròng (%)',
        'Financial',
        'Profitability',
        'Net profit margin',
        'RATIO'
    ),
    -- Valuation
    (
        'EPS_(VNĐ)',
        'EPS (VNĐ)',
        'Financial',
        'Valuation',
        'Earnings Per Share = Lợi nhuận sau thuế / Số lượng cổ phiếu',
        'RATIO'
    ),
    (
        'BVPS_(VNĐ)',
        'BVPS (VNĐ)',
        'Financial',
        'Valuation',
        'Book Value Per Share = Vốn chủ sở hữu / Số cổ phiếu',
        'RATIO'
    ),
    (
        'P_E',
        'P/E',
        'Financial',
        'Valuation',
        'Price to Earnings = Giá cổ phiếu / EPS',
        'RATIO'
    ),
    (
        'P_B',
        'P/B',
        'Financial',
        'Valuation',
        'Price to Book = Giá cổ phiếu / BVPS',
        'RATIO'
    ),
    -- Liquidity
    (
        'HỆ_SỐ_THANH_TOÁN_HIỆN_HÀNH',
        'Hệ số thanh toán hiện hành',
        'Financial',
        'Liquidity',
        'Current Ratio = Tài sản ngắn hạn / Nợ ngắn hạn',
        'RATIO'
    ),
    (
        'HỆ_SỐ_THANH_TOÁN_NHANH',
        'Hệ số thanh toán nhanh',
        'Financial',
        'Liquidity',
        'Quick Ratio = (TSNH - Hàng tồn kho) / Nợ ngắn hạn',
        'RATIO'
    ),
    -- Leverage
    (
        'TỶ_LỆ_NỢ_TRÊN_VỐN_CHỦ_SỞ_HỮU',
        'Tỷ lệ nợ trên vốn chủ sở hữu',
        'Financial',
        'Leverage',
        'Debt to Equity',
        'RATIO'
    ),
    (
        'TỶ_LỆ_NỢ_TRÊN_TỔNG_TÀI_SẢN',
        'Tỷ lệ nợ trên tổng tài sản',
        'Financial',
        'Leverage',
        'Debt to Assets',
        'RATIO'
    ),
    -- =====================================================
    -- BANKING SPECIFIC - Chỉ tiêu ngành ngân hàng (source = RATIO)
    -- =====================================================
    (
        'NIM_(_)',
        'NIM (%)',
        'Financial',
        'Banking',
        'Net Interest Margin',
        'RATIO'
    ),
    (
        'CIR_(_)',
        'CIR (%)',
        'Financial',
        'Banking',
        'Cost to Income Ratio',
        'RATIO'
    ),
    (
        'CASA_(_)',
        'CASA (%)',
        'Financial',
        'Banking',
        'Current Account Savings Account ratio',
        'RATIO'
    ),
    (
        'NPL_(_)',
        'NPL (%)',
        'Financial',
        'Banking',
        'Non-Performing Loan ratio',
        'RATIO'
    ),
    (
        'LDR_(_)',
        'LDR (%)',
        'Financial',
        'Banking',
        'Loan to Deposit Ratio',
        'RATIO'
    ),
    (
        'CAR_(_)',
        'CAR (%)',
        'Financial',
        'Banking',
        'Capital Adequacy Ratio',
        'RATIO'
    ),
    -- Banking Deposits & Loans (source = IS for banking)
    (
        'TIỀN_GỬI_KHÁCH_HÀNG',
        'Tiền gửi khách hàng',
        'Financial',
        'Banking',
        'Customer deposits',
        'BS'
    ),
    (
        'CHO_VAY_KHÁCH_HÀNG',
        'Cho vay khách hàng',
        'Financial',
        'Banking',
        'Loans to customers',
        'BS'
    ),
    (
        'THU_NHẬP_LÃI_THUẦN',
        'Thu nhập lãi thuần',
        'Financial',
        'Banking',
        'Net interest income',
        'IS'
    ),
    (
        'THU_NHẬP_TỪ_DỊCH_VỤ',
        'Thu nhập từ dịch vụ',
        'Financial',
        'Banking',
        'Fee and commission income',
        'IS'
    ),
    (
        'CHI_PHÍ_DỰ_PHÒNG',
        'Chi phí dự phòng',
        'Financial',
        'Banking',
        'Provision expenses',
        'IS'
    ) ON CONFLICT (metric_code) DO
UPDATE
SET metric_name = EXCLUDED.metric_name,
    category = EXCLUDED.category,
    sub_category = EXCLUDED.sub_category,
    formula_description = EXCLUDED.formula_description,
    source = EXCLUDED.source;