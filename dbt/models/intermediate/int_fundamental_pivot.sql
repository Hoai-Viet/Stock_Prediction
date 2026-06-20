-- int_fundamental_pivot: pivot financial metrics from staging.fact_financials
-- Mapping from ASCII-encoded metric_codes to readable column names
--
-- FIX v2:
--   1. Filter statement_type = 'year' → tránh lẫn quarter data vào annual pivot
--   2. P/E, P/B, P/S được tính lại từ giá đóng cửa cuối năm (int_price_daily)
--      thay vì dùng giá real-time từ vnstock RATIO API (gây lệch so với Fireant)
--   3. Expose raw EPS, BVPS, revenue để ML model dùng

{{ config(
    materialized='incremental',
    unique_key=['symbol_key', 'period_year', 'period_code'],
    indexes=[
        {'columns': ['symbol_key', 'period_year', 'period_code'], 'unique': true}
    ]
) }}

{% set has_source_created_at = false %}
{% if is_incremental() and execute %}
  {% set existing_columns = adapter.get_columns_in_relation(this) %}
  {% set existing_column_names = existing_columns | map(attribute='name') | map('lower') | list %}
  {% set has_source_created_at = 'source_created_at' in existing_column_names %}
{% endif %}


with 
{% if is_incremental() %}
new_data_keys as (
    select distinct symbol_key, period_year
    from {{ ref('src_fact_financials') }}
    where source_created_at >= (
        select coalesce(max(source_created_at), '1900-01-01'::timestamp)
        from {{ this }}
    ) - interval '2 days'
),
{% endif %}

base as (
    select
        symbol_key,
        stock_code,
        period_year,
        period_code,
        metric_code,
        metric_value,
        source_created_at,

        -- Map period_code -> period_end_date (đủ dùng để as-of join)
        case
            when upper(period_code) in ('Q1', '1') then make_date(period_year, 3, 31)
            when upper(period_code) in ('Q2', '2') then make_date(period_year, 6, 30)
            when upper(period_code) in ('Q3', '3') then make_date(period_year, 9, 30)
            when upper(period_code) in ('Q4', '4') then make_date(period_year, 12, 31)
            when upper(period_code) in ('Y', 'FY', 'YEAR') then make_date(period_year, 12, 31)
            else make_date(period_year, 12, 31)
        end as period_end_date
    from {{ ref('src_fact_financials') }}
    -- FIX: chỉ lấy annual data, tránh lẫn quarter data vào pivot
    -- statement_type='year' = dữ liệu cả năm
    -- period_raw=0 hoặc period_code='Y' = annual (crawl_bctc.py dùng period=0 cho annual)
    where statement_type = 'year'
      and period_code = 'Y'
    {% if is_incremental() %}
      and exists (
          select 1 from new_data_keys k 
          where k.symbol_key = src_fact_financials.symbol_key 
            and k.period_year = src_fact_financials.period_year
      )
    {% endif %}
),

-- Pivot raw metrics từ DB
pivoted as (
    select
        symbol_key,
        stock_code,
        period_year,
        period_code,
        period_end_date,
        max(source_created_at) as source_created_at,

        -- =====================================================
        -- BALANCE SHEET (BS) - Bảng cân đối kế toán
        -- =====================================================
        max(case when metric_code IN ('T_NG_C_NG_T_I_S_N____NG_', 'TONG_CONG_TAI_SAN', 'TONG_CONG_TAI_SAN_ONG') then nullif(metric_value, 0) end) as total_assets,
        max(case when metric_code IN ('TI_N_V__T__NG____NG_TI_N____NG_', 'TIEN_VA_TUONG_UONG_TIEN', 'TIEN_VA_TUONG_UONG_TIEN_ONG') then nullif(metric_value, 0) end) as cash,
        max(case when metric_code IN ('N__PH_I_TR_____NG_', 'NO_PHAI_TRA', 'NO_PHAI_TRA_ONG') then nullif(metric_value, 0) end) as total_liabilities,
        max(case when metric_code IN ('V_N_CH__S__H_U____NG_', 'VON_CHU_SO_HUU', 'VON_CHU_SO_HUU_ONG') then nullif(metric_value, 0) end) as equity,
        max(case when metric_code IN ('V_N_CSH_V_N__I_U_L_', 'OWNERS_EQUITY_CHARTER_CAPITAL', 'VON_GOP_CUA_CHU_SO_HUU_ONG', 'V_N_G_P_C_A_CH__S__H_U____NG_') then nullif(metric_value, 0) end) as charter_capital,
        max(case when metric_code IN ('L_I_CH_A_PH_N_PH_I____NG_', 'LAI_CHUA_PHAN_PHOI_ONG') then nullif(metric_value, 0) end) as retained_earnings,

        -- =====================================================
        -- INCOME STATEMENT (IS) - Báo cáo KQKD
        -- =====================================================
        max(case when metric_code IN ('DOANH_THU____NG_', 'DOANH_THU', 'DOANH_THU_ONG') then nullif(metric_value, 0) end) as revenue,
        max(case when metric_code IN ('L_I_NHU_N_SAU_THU__C_A_C____NG_C_NG_TY_M_____NG_', 'LOI_NHUAN_SAU_THUE_CUA_CO_ONG_CONG_TY_ME_ONG') then nullif(metric_value, 0) end) as net_profit,
        max(case when metric_code IN ('LN_TR__C_THU_', 'LN_TRUOC_THUE', 'NET_PROFIT_LOSS_BEFORE_TAX') then nullif(metric_value, 0) end) as profit_before_tax,
        max(case when metric_code IN ('T_NG_THU_NH_P_HO_T___NG', 'TONG_THU_NHAP_HOAT_ONG', 'OPERATING_PROFIT_BEFORE_CHANGES_IN_WORKING_CAPITAL') then nullif(metric_value, 0) end) as operating_income,
        max(case when metric_code IN ('L_I_NHU_N_THU_N', 'LOI_NHUAN_THUAN') then nullif(metric_value, 0) end) as net_profit_v2,

        -- =====================================================
        -- CASH FLOW (CF) - Lưu chuyển tiền tệ
        -- =====================================================
        max(case when metric_code IN ('NET_CASH_INFLOWS_OUTFLOWS_FROM_OPERATING_ACTIVITIES', 'NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES_BEFORE_BIT', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_KINH_DOANH', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_KINH_DOANH_ONG') then nullif(metric_value, 0) end) as cfo,
        max(case when metric_code IN ('NET_CASH_FLOWS_FROM_INVESTING_ACTIVITIES', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_AU_TU', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_AU_TU_ONG') then nullif(metric_value, 0) end) as cfi,
        max(case when metric_code IN ('CASH_FLOWS_FROM_FINANCIAL_ACTIVITIES', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_TAI_CHINH', 'LUU_CHUYEN_TIEN_THUAN_TU_HOAT_ONG_TAI_CHINH_ONG') then nullif(metric_value, 0) end) as cff,
        max(case when metric_code IN ('NET_INCREASE_DECREASE_IN_CASH_AND_CASH_EQUIVALENTS', 'LUU_CHUYEN_TIEN_THUAN_TRONG_KY', 'LUU_CHUYEN_TIEN_THUAN_TRONG_KY_ONG') then nullif(metric_value, 0) end) as net_cash_flow,

        -- =====================================================
        -- FINANCIAL RATIOS - Các chỉ số KHÔNG phụ thuộc giá thị trường
        -- (ROE, ROA, EPS, BVPS, margins, growth) → lấy thẳng từ API, đáng tin
        -- P/E, P/B, P/S → phụ thuộc giá thị trường → tính lại bên dưới từ giá cuối năm
        -- =====================================================
        max(case when metric_code IN ('ROE____', 'ROE') then nullif(metric_value, 0) end) as roe,
        max(case when metric_code IN ('ROA____', 'ROA') then nullif(metric_value, 0) end) as roa,
        -- EPS: đơn vị VND, không phụ thuộc giá → lấy thẳng
        max(case when metric_code IN ('EPS__VND_', 'EPS_VND', 'EPS') then nullif(metric_value, 0) end) as eps,
        -- BVPS: book value per share → không phụ thuộc giá → lấy thẳng
        max(case when metric_code IN ('BVPS__VND_', 'BVPS_VND', 'BVPS') then nullif(metric_value, 0) end) as bvps,
        max(case when metric_code IN ('BI_N_L_I_NHU_N_R_NG____', 'BIEN_LOI_NHUAN_RONG', 'NET_PROFIT_MARGIN') then nullif(metric_value, 0) end) as net_margin,
        max(case when metric_code IN ('__N_B_Y_T_I_CH_NH', 'ON_BAY_TAI_CHINH', 'FINANCIAL_LEVERAGE') then nullif(metric_value, 0) end) as financial_leverage,
        max(case when metric_code IN ('T_NG_TR__NG_DOANH_THU____', 'TANG_TRUONG_DOANH_THU') then nullif(metric_value, 0) end) as revenue_growth,
        max(case when metric_code IN ('T_NG_TR__NG_L_I_NHU_N____', 'TANG_TRUONG_LOI_NHUAN') then nullif(metric_value, 0) end) as profit_growth,
        -- Số CP lưu hành (triệu CP) → dùng để tính market cap, P/S thủ công
        max(case when metric_code IN ('S__CP_L_U_H_NH__TRI_U_CP_', 'SO_CP_LUU_HANH_TRIEU_CP', 'OUTSTANDING_SHARE_MIL_SHARES') then nullif(metric_value, 0) end) as shares_outstanding,

        -- P/E, P/B, P/S raw từ API (giá real-time khi crawl) — GIỮ LẠI để debug
        max(case when metric_code IN ('P_E', 'PE') then nullif(metric_value, 0) end) as pe_raw,
        max(case when metric_code IN ('P_B', 'PB') then nullif(metric_value, 0) end) as pb_raw,
        max(case when metric_code IN ('P_S', 'PS') then nullif(metric_value, 0) end) as ps_raw,
        max(case when metric_code IN ('P_CASH_FLOW', 'P_CF') then nullif(metric_value, 0) end) as p_cash_flow_raw,

        -- =====================================================
        -- BANKING SPECIFIC
        -- =====================================================
        max(case when metric_code IN ('CHO_VAY_KH_CH_H_NG', '_CHO_VAY_KH_CH_H_NG', 'CHO_VAY_KHACH_HANG') then nullif(metric_value, 0) end) as customer_loans,
        max(case when metric_code IN ('TI_N_G_I_C_A_KH_CH_H_NG', 'TIEN_GUI_CUA_KHACH_HANG') then nullif(metric_value, 0) end) as customer_deposits,
        max(case when metric_code IN ('THU_NH_P_L_I_THU_N', 'THU_NHAP_LAI_THUAN') then nullif(metric_value, 0) end) as net_interest_income,
        max(case when metric_code IN ('CHI_PH__D__PH_NG_R_I_RO_T_N_D_NG', 'CHI_PHI_DU_PHONG_RUI_RO_TIN_DUNG', 'DU_PHONG_RUI_RO_CHO_VAY_KHACH_HANG') then nullif(metric_value, 0) end) as provision_expense,
        max(case when metric_code IN ('GI__TR__R_NG_T_I_S_N___U_T_', 'GIA_TRI_RONG_TAI_SAN_AU_TU') then nullif(metric_value, 0) end) as net_asset_value

    from base
    group by symbol_key, stock_code, period_year, period_code, period_end_date
),

-- Lấy giá đóng cửa cuối năm từ int_price_daily
-- Dùng DISTINCT ON để lấy ngày giao dịch cuối cùng của mỗi năm (thường < 31/12 vì nghỉ lễ)
eoy_price as (
    select distinct on (symbol_key, price_year)
        symbol_key,
        extract(year from trade_date)::int as price_year,
        trade_date                          as last_trade_date,
        close_price                         as close_price_eoy
    from {{ ref('int_price_daily') }}
    order by symbol_key, extract(year from trade_date)::int, trade_date desc
)

select
    pv.symbol_key,
    pv.period_year,
    pv.period_code,
    pv.period_end_date,
    pv.source_created_at,

    -- Fundamentals (không phụ thuộc giá thị trường) — giữ nguyên
    pv.total_assets,
    pv.cash,
    pv.total_liabilities,
    pv.equity,
    pv.charter_capital,
    pv.retained_earnings,
    pv.revenue,
    pv.net_profit,
    pv.profit_before_tax,
    pv.operating_income,
    pv.net_profit_v2,
    pv.cfo,
    pv.cfi,
    pv.cff,
    pv.net_cash_flow,
    pv.roe,
    pv.roa,
    pv.eps,
    pv.bvps,
    pv.net_margin,
    pv.financial_leverage,
    pv.revenue_growth,
    pv.profit_growth,
    pv.shares_outstanding,
    pv.customer_loans,
    pv.customer_deposits,
    pv.net_interest_income,
    pv.provision_expense,
    pv.net_asset_value,

    -- Giá đóng cửa cuối năm (VND)
    ep.close_price_eoy,

    -- =====================================================
    -- P/E, P/B, P/S TÍNH LẠI từ giá cuối năm
    -- → kết quả khớp với Fireant / CafeF
    -- =====================================================

    -- P/E = giá_cuối_năm / EPS
    -- EPS đơn vị VND, close_price_eoy đơn vị VND
    case
        when pv.eps is not null and pv.eps <> 0 and ep.close_price_eoy is not null
        then round((ep.close_price_eoy / pv.eps)::numeric, 2)
        else null
    end as pe,

    -- P/B = giá_cuối_năm / BVPS
    case
        when pv.bvps is not null and pv.bvps <> 0 and ep.close_price_eoy is not null
        then round((ep.close_price_eoy / pv.bvps)::numeric, 2)
        else null
    end as pb,

    -- P/S = market_cap / revenue
    -- market_cap = close_price_eoy × shares_outstanding × 1,000,000 (CP → đơn vị)
    -- revenue đơn vị: tỷ VND → × 1,000,000,000
    -- shares_outstanding đơn vị: triệu CP → × 1,000,000
    -- market_cap (đồng) = close_price_eoy × shares_outstanding × 1e6
    -- revenue (đồng)    = revenue × 1e9
    -- P/S = (price × shares_outstanding × 1e6) / (revenue × 1e9)
    --      = (price × shares_outstanding) / (revenue × 1e3)
    case
        when pv.revenue is not null and pv.revenue <> 0
         and pv.shares_outstanding is not null
         and ep.close_price_eoy is not null
        then round(
            (ep.close_price_eoy * pv.shares_outstanding
             / (pv.revenue * 1000.0))::numeric, 2)
        else null
    end as ps,

    -- Raw values từ API (giữ lại để debug / so sánh)
    pv.pe_raw,
    pv.pb_raw,
    pv.ps_raw,
    pv.p_cash_flow_raw

from pivoted pv
left join eoy_price ep
    on ep.symbol_key = pv.symbol_key
   and ep.price_year = pv.period_year

