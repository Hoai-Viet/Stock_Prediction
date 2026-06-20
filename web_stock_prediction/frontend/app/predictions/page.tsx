"use client";

import { useEffect, useState, useMemo } from "react";
import dynamic from 'next/dynamic';
import { AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart } from 'recharts';
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { useRegistration } from "@/components/RegistrationProvider";

const CandleChart = dynamic(() => import('../../components/CandleChart'), { ssr: false });

// --- Mock Data ---
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const SYMBOL_DISPLAY_LIMIT = 5;

const PREDICTION_TEXT = {
    en: {
        loadingData: "Loading data...",
        loadingTechnical: "Loading technical metrics...",
        noTechnical: "No technical metrics found.",
        title: "Stock Predictions",
        updated: "Updated",
        more: "more",
        showLess: "show less",
        loadingCandles: "Loading candles...",
        noCandles: "No candle data found.",
        volume: "Volume",
        trading: "Trading",
        technicalAnalysis: "Technical Analysis",
        todayPrediction: "Today's Prediction",
        loadingPrediction: "Loading latest prediction...",
        signal: "Signal",
        confidence: "Confidence",
        noPrediction: "No prediction available for this symbol.",
        holdTitle: "No clear signal yet",
        holdDescription: "Today does not have enough confirmed signals for a prediction. Please come back tomorrow for the next market update.",
        membersOnly: "Members only",
        unlockTitle: "Unlock today's prediction",
        unlockDescription: "Register to receive this symbol's latest BUY/SELL signal and priority market updates.",
        registerPrompt: "Register to receive more information",
        validationHistory: "BUY/SELL Validation History",
        accurate: "accurate",
        date: "Date",
        predicted: "Predicted",
        actual: "Actual",
        change: "Change",
        result: "Result",
        loadingHistory: "Loading validation history...",
        noHistory: "No BUY/SELL validation history found.",
        relatedNews: "Related News",
        viewAll: "View all",
        loadingNews: "Loading market news...",
        noNews: "No market news available.",
        financialReports: "Financial Report Charts",
        annualReports: "Annual reports",
        incomeStatement: "Income Statement",
        balanceSheet: "Balance Sheet",
        cashFlow: "Cash Flow",
        operatingIncome: "Operating income",
        netInterestIncome: "Net interest income",
        netProfit: "Net profit",
        totalAssets: "Total assets",
        customerDeposits: "Customer deposits",
        operatingCashFlow: "Operating cash flow",
        trillionVnd: "VND tn",
        loadingFinancials: "Loading financial reports...",
        noFinancials: "No annual financial reports found for this symbol.",
        warehouseDescription: "Prediction data is available for this symbol in the warehouse.",
        banking: "Banking",
    },
    vi: {
        loadingData: "Đang tải dữ liệu...",
        loadingTechnical: "Đang tải chỉ số kỹ thuật...",
        noTechnical: "Không tìm thấy chỉ số kỹ thuật.",
        title: "Dự báo cổ phiếu",
        updated: "Cập nhật",
        more: "mã khác",
        showLess: "thu gọn",
        loadingCandles: "Đang tải dữ liệu giá...",
        noCandles: "Không tìm thấy dữ liệu giá.",
        volume: "Khối lượng",
        trading: "Ngày giao dịch",
        technicalAnalysis: "Phân tích kỹ thuật",
        todayPrediction: "Dự báo hôm nay",
        loadingPrediction: "Đang tải dự báo mới nhất...",
        signal: "Tín hiệu",
        confidence: "Độ tin cậy",
        noPrediction: "Chưa có dự báo cho mã này.",
        holdTitle: "Chưa có tín hiệu rõ ràng",
        holdDescription: "Hôm nay chưa có đủ tín hiệu để dự đoán. Hãy quay lại vào ngày mai nhé.",
        membersOnly: "Dành cho thành viên",
        unlockTitle: "Mở khóa dự báo hôm nay",
        unlockDescription: "Đăng ký để nhận tín hiệu MUA/BÁN mới nhất của mã này và các cập nhật thị trường ưu tiên.",
        registerPrompt: "Đăng ký để nhận thêm thông tin",
        validationHistory: "Lịch sử kiểm chứng MUA/BÁN",
        accurate: "chính xác",
        date: "Ngày",
        predicted: "Dự báo",
        actual: "Thực tế",
        change: "Thay đổi",
        result: "Kết quả",
        loadingHistory: "Đang tải lịch sử kiểm chứng...",
        noHistory: "Không tìm thấy lịch sử kiểm chứng MUA/BÁN.",
        relatedNews: "Tin tức liên quan",
        viewAll: "Xem tất cả",
        loadingNews: "Đang tải tin thị trường...",
        noNews: "Chưa có tin thị trường.",
        financialReports: "Biểu đồ báo cáo tài chính",
        annualReports: "Báo cáo năm",
        incomeStatement: "Kết quả kinh doanh",
        balanceSheet: "Bảng cân đối kế toán",
        cashFlow: "Dòng tiền",
        operatingIncome: "Tổng thu nhập hoạt động",
        netInterestIncome: "Thu nhập lãi thuần",
        netProfit: "Lợi nhuận sau thuế",
        totalAssets: "Tổng tài sản",
        customerDeposits: "Tiền gửi khách hàng",
        operatingCashFlow: "Dòng tiền từ hoạt động",
        trillionVnd: "nghìn tỷ VND",
        loadingFinancials: "Đang tải báo cáo tài chính...",
        noFinancials: "Không có báo cáo tài chính năm cho mã này.",
        warehouseDescription: "Dữ liệu dự báo của mã này đã có trong kho dữ liệu.",
        banking: "Ngân hàng",
    },
};

type PredictionSymbol = {
    symbol_key: number;
    symbol_code: string;
    company_name?: string | null;
    sector_name?: string | null;
    description?: string | null;
    latest_prediction?: string | null;
};

type TechnicalMetricRow = {
    period_date: string;
    date: string;
    close: number | null;
    volume: number | null;
    vol_avg: number | null;
    rsi: number | null;
    macd: number | null;
    macd_signal: number | null;
    macd_hist: number | null;
    ma_20: number | null;
    bb_upper: number | null;
    bb_lower: number | null;
    obv: number | null;
    obv_avg?: number | null;
};

type CandleRow = {
    time: string | number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
};

type PredictionHistoryRow = {
    trade_date: string;
    latest_trade_date?: string | null;
    predicted_label: string;
    actual_direction: string | null;
    is_correct: boolean | null;
    model_version: string;
    generated_at: string;
    close_price: number | null;
    confidence_accuracy?: number | null;
    change: number | null;
    change_pct: number | null;
};

type CurrentPrediction = {
    trade_date: string;
    predicted_label: "BUY" | "SELL" | "HOLD";
    signal_strength: "CERTAIN" | "LIKELY" | "HOLD";
    confidence?: number | null;
    display_confidence?: number | null;
    rule_id?: number | null;
    rule_combo?: string | null;
    missing_feature?: string | null;
};

type SignalDisplayValue = "BUY" | "SELL" | "HOLD" | "CERTAIN" | "LIKELY";

const SIGNAL_DISPLAY_TEXT: Record<"en" | "vi", Record<SignalDisplayValue, string>> = {
    en: {
        BUY: "BUY",
        SELL: "SELL",
        HOLD: "HOLD",
        CERTAIN: "CERTAIN",
        LIKELY: "LIKELY",
    },
    vi: {
        BUY: "MUA",
        SELL: "BÁN",
        HOLD: "GIỮ",
        CERTAIN: "CHẮC CHẮN",
        LIKELY: "CÓ KHẢ NĂNG",
    },
};

const getSignalDisplayText = (value: string | null | undefined, language: "en" | "vi") => {
    if (!value) return "N/A";
    return SIGNAL_DISPLAY_TEXT[language][value as SignalDisplayValue] || value;
};

type NewsItem = {
    id: string;
    title: string;
    category: string;
    source: string;
    timestamp: string;
    summary: string;
    url: string;
};

type FinancialReportRow = {
    year: number;
    operating_income: number | null;
    net_interest_income: number | null;
    net_profit: number | null;
    total_assets: number | null;
    customer_deposits: number | null;
    operating_cash_flow: number | null;
};

const generateCandleData = (symbol: string) => {
    const data = [];
    let basePrice = symbol === "FPT" ? 78 : symbol === "VCB" ? 92 : symbol === "VIC" ? 42 : 65;
    const startDate = new Date("2026-01-02");
    for (let i = 0; i < 60; i++) {
        const d = new Date(startDate);
        d.setDate(d.getDate() + i);
        if (d.getDay() === 0 || d.getDay() === 6) continue;
        const change = (Math.random() - 0.48) * 3;
        const open = basePrice;
        const close = +(basePrice + change).toFixed(1);
        const high = +(Math.max(open, close) + Math.random() * 1.5).toFixed(1);
        const low = +(Math.min(open, close) - Math.random() * 1.5).toFixed(1);
        data.push({
            time: d.toISOString().split("T")[0],
            open, high, low, close,
            volume: Math.floor(Math.random() * 15000000) + 1000000
        });
        basePrice = close;
    }
    return data;
};

const generateTAChartData = (symbol: string) => {
    const data = [];
    const baseRsi = symbol === "FPT" ? 55 : symbol === "VCB" ? 68 : 50;
    const baseMacd = symbol === "FPT" ? 0.3 : symbol === "VCB" ? 1.0 : 0.1;
    const baseVol = symbol === "FPT" ? 8 : symbol === "VCB" ? 12 : 5;
    let close = symbol === "FPT" ? 78.3 : symbol === "VCB" ? 93.5 : symbol === "VIC" ? 43.2 : 66.1;
    let obv = symbol === "FPT" ? 120 : symbol === "VCB" ? 180 : 95;
    for (let i = 0; i < 30; i++) {
        const d = new Date("2026-03-01");
        d.setDate(d.getDate() + i);
        if (d.getDay() === 0 || d.getDay() === 6) continue;
        const label = `${d.getDate()}/${d.getMonth() + 1}`;
        const vol = +(baseVol + (Math.random() - 0.3) * 8).toFixed(1);
        const priorClose = close;
        close = +(close + (Math.random() - 0.48) * 1.8).toFixed(1);
        obv = +(obv + (close >= priorClose ? vol : -vol)).toFixed(1);
        const ma20 = +(close + (Math.random() - 0.5) * 1.4).toFixed(1);
        const bandWidth = +(1.4 + Math.random() * 1.2).toFixed(1);
        data.push({
            date: label,
            close,
            volume: Math.abs(vol),
            vol_avg: baseVol,
            rsi: +(baseRsi + (Math.random() - 0.45) * 20).toFixed(1),
            macd: +(baseMacd + (Math.random() - 0.5) * 1.5).toFixed(2),
            macd_signal: +(baseMacd - 0.1 + (Math.random() - 0.5) * 1.2).toFixed(2),
            macd_hist: +((Math.random() - 0.45) * 0.8).toFixed(2),
            ma_20: ma20,
            bb_upper: +(ma20 + bandWidth).toFixed(1),
            bb_lower: +(ma20 - bandWidth).toFixed(1),
            obv,
            obv_avg: +(obv + (Math.random() - 0.5) * 8).toFixed(1),
        });
    }
    return data;
};

const classifyDirection = (changePct: number) => {
    if (changePct >= 2) return "BUY";
    if (changePct <= -2) return "SELL";
    return "HOLD";
};

const pickPredictedLabel = () => {
    const roll = Math.random();
    if (roll < 0.36) return "BUY";
    if (roll < 0.68) return "SELL";
    return "HOLD";
};

const generatePredictionHistory = (symbol: string) => {
    const history = [];
    const today = new Date("2026-04-09");
    let price = symbol === "FPT" ? 78.3 : symbol === "VCB" ? 93.5 : symbol === "VIC" ? 43.2 : 66.1;
    for (let i = 1; i <= 20; i++) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        if (d.getDay() === 0 || d.getDay() === 6) continue;
        const predictedLabel = pickPredictedLabel();
        const actualChangePct = +(((Math.random() - 0.5) * 6)).toFixed(2);
        const closePrice = +price.toFixed(1);
        const actualChange = +((closePrice * actualChangePct) / 100).toFixed(2);
        const actualLabel = classifyDirection(actualChangePct);
        const isCorrect = predictedLabel === actualLabel;
        history.push({
            date: d.toISOString().split("T")[0],
            predicted_label: predictedLabel,
            actual_label: actualLabel,
            is_correct: isCorrect,
            close_price: closePrice,
            change: actualChange,
            change_pct: actualChangePct,
            confidence: +(predictedLabel === "HOLD" ? 48 + Math.random() * 18 : 60 + Math.random() * 30).toFixed(1),
            model: "v1.2.0"
        });
        price = +(closePrice - actualChange).toFixed(1);
    }
    return history;
};

const todayPrediction: Record<string, any> = {
    FPT: { predicted_label: "BUY", confidence: 78.5, model: "v1.2.0", entry_window: "MORNING", generated_at: "09/04/2026 11:00" },
    VCB: { predicted_label: "SELL", confidence: 65.2, model: "v1.2.0", entry_window: "AFTERNOON", generated_at: "09/04/2026 11:00" },
    VIC: { predicted_label: "BUY", confidence: 72.8, model: "v1.2.0", entry_window: "OPEN", generated_at: "09/04/2026 11:00" },
    VNM: { predicted_label: "BUY", confidence: 81.3, model: "v1.2.0", entry_window: "MORNING", generated_at: "09/04/2026 11:00" },
    HPG: { predicted_label: "HOLD", confidence: 56.1, model: "v1.2.0", entry_window: "NONE", generated_at: "09/04/2026 11:00" },
    MWG: { predicted_label: "BUY", confidence: 74.1, model: "v1.2.0", entry_window: "CLOSE", generated_at: "09/04/2026 11:00" },
    TCB: { predicted_label: "SELL", confidence: 69.7, model: "v1.2.0", entry_window: "AFTERNOON", generated_at: "09/04/2026 11:00" },
    VHM: { predicted_label: "BUY", confidence: 85.0, model: "v1.2.0", entry_window: "OPEN", generated_at: "09/04/2026 11:00" },
};

const stockInfo: Record<string, any> = {
    FPT: { name: "FPT Corporation", fullName: "FPT Corporation", exchange: "HOSE", price: 78.30, change: -0.80, changePct: -1.01, sector: "Technology", logoColors: ["#F37021", "#00A650", "#0072BC"] },
    VCB: { name: "Vietcombank", fullName: "Joint Stock Commercial Bank for Foreign Trade of Vietnam", exchange: "HOSE", price: 93.50, change: 1.20, changePct: 1.30, sector: "Banking", logoColors: ["#006838", "#006838", "#006838"] },
    VIC: { name: "Vingroup JSC", fullName: "Vingroup Joint Stock Company", exchange: "HOSE", price: 43.20, change: -0.30, changePct: -0.69, sector: "Real Estate", logoColors: ["#D32F2F", "#D32F2F", "#D32F2F"] },
    VNM: { name: "Vinamilk", fullName: "Vietnam Dairy Products Joint Stock Company", exchange: "HOSE", price: 66.10, change: 0.50, changePct: 0.76, sector: "Consumer Goods", logoColors: ["#0066B3", "#0066B3", "#E31E24"] },
    HPG: { name: "Hoa Phat Group", fullName: "Hoa Phat Group Joint Stock Company", exchange: "HOSE", price: 25.30, change: -0.45, changePct: -1.75, sector: "Steel & Materials", logoColors: ["#C62828", "#C62828", "#FF8F00"] },
    MWG: { name: "Mobile World Group", fullName: "Mobile World Investment Corporation", exchange: "HOSE", price: 54.80, change: 0.90, changePct: 1.67, sector: "Retail", logoColors: ["#FFD600", "#FFD600", "#000000"] },
    TCB: { name: "Techcombank", fullName: "Vietnam Technological and Commercial Joint Stock Bank", exchange: "HOSE", price: 34.50, change: -0.20, changePct: -0.58, sector: "Banking", logoColors: ["#D32F2F", "#D32F2F", "#1A237E"] },
    VHM: { name: "Vinhomes JSC", fullName: "Vinhomes Joint Stock Company", exchange: "HOSE", price: 40.80, change: 1.50, changePct: 3.82, sector: "Real Estate", logoColors: ["#1565C0", "#1565C0", "#1565C0"] },
};

const companyDescriptions: Record<string, { en: string; vi: string }> = {
    FPT: {
        en: "Vietnam's leading technology corporation, founded in 1988. FPT operates in technology, telecommunications, and education.",
        vi: "Tập đoàn công nghệ hàng đầu Việt Nam, hoạt động trong ba lĩnh vực chính: công nghệ, viễn thông và giáo dục.",
    },
    VCB: {
        en: "Vietnam's largest state-owned commercial bank by market cap, with strengths in trade finance, foreign exchange, and international payments.",
        vi: "Một trong những ngân hàng thương mại lớn nhất Việt Nam, có thế mạnh về tài trợ thương mại, ngoại hối và thanh toán quốc tế.",
    },
    VIC: {
        en: "Vietnam's largest private conglomerate, with major investments in real estate, hospitality, healthcare, education, retail, and technology.",
        vi: "Tập đoàn tư nhân đa ngành lớn tại Việt Nam, hoạt động trong bất động sản, du lịch, y tế, giáo dục, bán lẻ và công nghệ.",
    },
    VNM: {
        en: "Vietnam's largest dairy producer, with a broad domestic distribution network and exports to international markets.",
        vi: "Doanh nghiệp sữa hàng đầu Việt Nam, sở hữu mạng lưới phân phối rộng và xuất khẩu tới nhiều thị trường quốc tế.",
    },
    HPG: {
        en: "Vietnam's largest steel producer and a diversified industrial group active in steel, real estate, agriculture, and consumer goods.",
        vi: "Nhà sản xuất thép lớn tại Việt Nam, đồng thời hoạt động trong bất động sản, nông nghiệp và hàng tiêu dùng.",
    },
    MWG: {
        en: "Vietnam's leading electronics and digital retail group, operating nationwide consumer retail chains.",
        vi: "Tập đoàn bán lẻ hàng đầu Việt Nam, vận hành nhiều chuỗi điện tử, điện máy và hàng tiêu dùng trên toàn quốc.",
    },
    TCB: {
        en: "One of Vietnam's largest private commercial banks, focused on digital banking, consumer lending, and corporate finance.",
        vi: "Một trong những ngân hàng thương mại tư nhân lớn tại Việt Nam, tập trung vào ngân hàng số, tín dụng tiêu dùng và tài chính doanh nghiệp.",
    },
    VHM: {
        en: "A major Vietnamese real estate developer specializing in large-scale urban areas, apartments, and villas.",
        vi: "Doanh nghiệp phát triển bất động sản lớn tại Việt Nam, chuyên về các khu đô thị, căn hộ và biệt thự quy mô lớn.",
    },
};

const bankDescriptionsVi: Record<string, string> = {
    ACB: "Ngân hàng thương mại cổ phần định hướng bán lẻ, có thế mạnh về khách hàng cá nhân và doanh nghiệp vừa và nhỏ.",
    BAB: "Ngân hàng thương mại cổ phần tập trung vào hoạt động ngân hàng bán lẻ và phục vụ doanh nghiệp trong nước.",
    BID: "Ngân hàng thương mại lớn tại Việt Nam, cung cấp dịch vụ tài chính cho khách hàng cá nhân, doanh nghiệp và các dự án đầu tư.",
    CTG: "Ngân hàng thương mại lớn với mạng lưới rộng, có thế mạnh về tài chính doanh nghiệp, bán lẻ và thanh toán.",
    EIB: "Ngân hàng thương mại cổ phần có thế mạnh về xuất nhập khẩu, ngoại hối và các dịch vụ tài chính doanh nghiệp.",
    HDB: "Ngân hàng thương mại cổ phần phát triển mạnh ở mảng bán lẻ, tài chính tiêu dùng và khách hàng doanh nghiệp.",
    LPB: "Ngân hàng thương mại cổ phần sở hữu mạng lưới rộng, tập trung vào bán lẻ và phục vụ khách hàng trên toàn quốc.",
    MBB: "Ngân hàng thương mại cổ phần có nền tảng số mạnh, phục vụ khách hàng cá nhân, doanh nghiệp và hệ sinh thái quân đội.",
    MSB: "Ngân hàng thương mại cổ phần tập trung vào ngân hàng số, khách hàng cá nhân và doanh nghiệp vừa và nhỏ.",
    NAB: "Ngân hàng thương mại cổ phần định hướng bán lẻ, cung cấp sản phẩm cho khách hàng cá nhân và doanh nghiệp.",
    NVB: "Ngân hàng thương mại cổ phần tập trung vào bán lẻ, huy động vốn và tín dụng cho khách hàng trong nước.",
    OCB: "Ngân hàng thương mại cổ phần phát triển ngân hàng số, bán lẻ và các giải pháp tài chính doanh nghiệp.",
    PGB: "Ngân hàng thương mại cổ phần cung cấp dịch vụ bán lẻ và doanh nghiệp, có liên kết với hệ sinh thái xăng dầu.",
    SGB: "Ngân hàng thương mại cổ phần hoạt động chủ yếu trong lĩnh vực bán lẻ và tài trợ doanh nghiệp trong nước.",
    SHB: "Ngân hàng thương mại cổ phần có mạng lưới rộng, phục vụ khách hàng cá nhân, doanh nghiệp và các dự án đầu tư.",
    SSB: "Ngân hàng thương mại cổ phần tập trung vào bán lẻ, ngân hàng số và tài chính cho doanh nghiệp.",
    STB: "Ngân hàng thương mại cổ phần có mạng lưới bán lẻ lớn, cung cấp đa dạng sản phẩm tài chính trên toàn quốc.",
    TCB: "Một trong những ngân hàng thương mại tư nhân lớn tại Việt Nam, tập trung vào ngân hàng số, tín dụng tiêu dùng và tài chính doanh nghiệp.",
    TPB: "Ngân hàng thương mại cổ phần nổi bật với nền tảng ngân hàng số và các sản phẩm tài chính dành cho khách hàng cá nhân.",
    VAB: "Ngân hàng thương mại cổ phần cung cấp dịch vụ bán lẻ và tài chính doanh nghiệp tại thị trường Việt Nam.",
    VCB: "Một trong những ngân hàng thương mại lớn nhất Việt Nam, có thế mạnh về tài trợ thương mại, ngoại hối và thanh toán quốc tế.",
    VIB: "Ngân hàng thương mại cổ phần tập trung vào bán lẻ, thẻ tín dụng, cho vay mua nhà và mua ô tô.",
    VPB: "Ngân hàng thương mại cổ phần lớn, phát triển mạnh ở mảng bán lẻ, tài chính tiêu dùng và ngân hàng số.",
};

const PERIOD_TABS = ["1D", "1M", "3M", "6M", "1Y", "All"];

const formatChartAxis = (value: number) => {
    const absoluteValue = Math.abs(value);
    if (absoluteValue >= 1000) return `${(value / 1000).toFixed(1)}k`;
    if (absoluteValue >= 100) return value.toFixed(0);
    return value.toFixed(1);
};

const readRequestedSymbol = () => {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get("symbol")?.toUpperCase() || null;
};

const formatCandleTime = (time: string | number, period: string) => {
    const date = typeof time === "number" ? new Date(time * 1000) : new Date(time);
    if (Number.isNaN(date.getTime())) return String(time);
    if (period === "1Y") return String(date.getFullYear());
    if (period !== "1D") return `${String(date.getMonth() + 1).padStart(2, "0")}/${date.getFullYear()}`;
    return date.toLocaleDateString("en-GB");
};
const TA_INDICATORS = ["Volume", "RSI", "MACD", "Bollinger", "OBV"];

const getSignalStrength = (confidence: number) => {
    if (confidence >= 80) return "STRONG";
    if (confidence >= 65) return "MODERATE";
    if (confidence >= 0) return "WEAK";
    return "UNKNOWN";
};

const getPredictionTone = (label: string) => {
    switch (label) {
        case "BUY":
            return {
                text: "text-buy",
                softBg: "bg-buy/10 border border-buy/30 text-buy",
                bar: "bg-gradient-to-r from-buy/60 to-buy",
                badge: "+",
            };
        case "SELL":
            return {
                text: "text-sell",
                softBg: "bg-sell/10 border border-sell/30 text-sell",
                bar: "bg-gradient-to-r from-sell/60 to-sell",
                badge: "-",
            };
        default:
            return {
                text: "text-gray-300",
                softBg: "bg-gray-500/10 border border-gray-500/30 text-gray-300",
                bar: "bg-gradient-to-r from-gray-500/60 to-gray-400",
                badge: "~",
            };
    }
};

const MiniTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="rounded-md border border-border-subtle bg-white px-2.5 py-1.5 text-[11px] shadow-lg shadow-slate-200/70">
                <div className="text-gray-400 mb-0.5">{label}</div>
                {payload.map((p: any, i: number) => (
                    <div key={i} className="font-semibold" style={{ color: p.color }}>
                        {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

// --- Individual TA Chart Components ---
function VolumeChart({ data }: { data: any[] }) {
    const { language } = useLanguage();
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-500">
                    {language === "vi" ? "Khối lượng (triệu cổ phiếu) so với trung bình 20 ngày" : "Volume (M shares) vs 20-day average"}
                </span>
                <span className="text-[11px] font-semibold text-text-primary">{data[data.length - 1]?.volume.toFixed(1)}M</span>
            </div>
            <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} interval={4} />
                        <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<MiniTooltip />} />
                        <Bar dataKey="volume" name="Volume" fill="#15212f" opacity={0.28} radius={[2, 2, 0, 0]} />
                        <Line type="monotone" dataKey="vol_avg" name="Avg" stroke="#d99a16" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-3 h-2 bg-accent-purple/50 inline-block rounded-sm" /> {language === "vi" ? "Khối lượng" : "Volume"}</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-[#FF9F43] inline-block" /> {language === "vi" ? "TB 20 ngày" : "20-day Avg"}</span>
            </div>
        </div>
    );
}

function RSIChart({ data }: { data: any[] }) {
    const { language } = useLanguage();
    const latest = data[data.length - 1];
    const status = latest.rsi > 70
        ? (language === "vi" ? "Quá mua" : "Overbought")
        : latest.rsi < 30
            ? (language === "vi" ? "Quá bán" : "Oversold")
            : (language === "vi" ? "Trung tính" : "Neutral");
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-500">RSI (14) - {status}</span>
                <span className={`text-[11px] font-semibold ${latest.rsi > 70 ? "text-sell" : latest.rsi < 30 ? "text-buy" : "text-text-primary"}`}>{latest.rsi}</span>
            </div>
            <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                        <defs>
                            <linearGradient id="rsiGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#15212f" stopOpacity={0.18} />
                                <stop offset="100%" stopColor="#15212f" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} interval={4} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<MiniTooltip />} />
                        <ReferenceLine y={70} stroke="#FF4D4F" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <ReferenceLine y={30} stroke="#0f9f6e" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <Area type="monotone" dataKey="rsi" name="RSI" stroke="#15212f" fill="url(#rsiGrad)" strokeWidth={2} dot={false} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-sell inline-block" /> 70 ({language === "vi" ? "Quá mua" : "Overbought"})</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-buy inline-block" /> 30 ({language === "vi" ? "Quá bán" : "Oversold"})</span>
            </div>
        </div>
    );
}

function MACDChart({ data }: { data: any[] }) {
    const { language } = useLanguage();
    const latest = data[data.length - 1];
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-500">MACD (12, 26, 9)</span>
                <span className={`text-[11px] font-semibold ${latest.macd > latest.macd_signal ? "text-buy" : "text-sell"}`}>
                    {latest.macd} / {latest.macd_signal}
                </span>
            </div>
            <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} interval={4} />
                        <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<MiniTooltip />} />
                        <ReferenceLine y={0} stroke="#374151" strokeOpacity={0.5} />
                        <Bar dataKey="macd_hist" name="Histogram" fill="#15212f" opacity={0.28} radius={[2, 2, 0, 0]} />
                        <Line type="monotone" dataKey="macd" name="MACD" stroke="#526173" strokeWidth={1.5} dot={false} />
                        <Line type="monotone" dataKey="macd_signal" name="Signal" stroke="#FF4D4F" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-accent-blue inline-block" /> MACD</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-sell inline-block" /> {language === "vi" ? "Tín hiệu" : "Signal"}</span>
                <span className="flex items-center gap-1"><span className="w-3 h-2 bg-accent-purple/40 inline-block rounded-sm" /> {language === "vi" ? "Biểu đồ cột" : "Histogram"}</span>
            </div>
        </div>
    );
}

function BollingerChart({ data }: { data: any[] }) {
    const { language } = useLanguage();
    const latest = data[data.length - 1];
    const status = latest.close > latest.bb_upper
        ? (language === "vi" ? "Bứt phá dải trên" : "Upper breakout")
        : latest.close < latest.bb_lower
            ? (language === "vi" ? "Phá vỡ dải dưới" : "Lower breakdown")
            : (language === "vi" ? "Trong dải" : "Inside bands");
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-500">Bollinger Bands (20, 2) - {status}</span>
                <span className="text-[11px] font-semibold text-text-primary">{latest.bb_lower} / {latest.bb_upper}</span>
            </div>
            <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} interval={4} />
                        <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<MiniTooltip />} />
                        <Line type="monotone" dataKey="close" name="Close" stroke="#15212f" strokeWidth={1.5} dot={false} />
                        <Line type="monotone" dataKey="bb_upper" name="Upper" stroke="#FF4D4F" strokeWidth={1.5} dot={false} />
                        <Line type="monotone" dataKey="ma_20" name="MA20" stroke="#d99a16" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                        <Line type="monotone" dataKey="bb_lower" name="Lower" stroke="#526173" strokeWidth={1.5} dot={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-accent-purple inline-block" /> {language === "vi" ? "Đóng cửa" : "Close"}</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-sell inline-block" /> {language === "vi" ? "Dải trên" : "Upper"}</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-hold inline-block" /> MA20</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-accent-blue inline-block" /> {language === "vi" ? "Dải dưới" : "Lower"}</span>
            </div>
        </div>
    );
}

function OBVChart({ data }: { data: any[] }) {
    const { language } = useLanguage();
    const latest = data[data.length - 1];
    const status = latest.obv >= latest.obv_avg
        ? (language === "vi" ? "Tích lũy" : "Accumulation")
        : (language === "vi" ? "Phân phối" : "Distribution");
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-gray-500">On-Balance Volume - {status}</span>
                <span className={`text-[11px] font-semibold ${latest.obv >= latest.obv_avg ? "text-buy" : "text-sell"}`}>{latest.obv.toFixed(1)}M</span>
            </div>
            <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                        <defs>
                            <linearGradient id="obvGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#526173" stopOpacity={0.18} />
                                <stop offset="100%" stopColor="#526173" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} interval={4} />
                        <YAxis tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<MiniTooltip />} />
                        <Area type="monotone" dataKey="obv" name="OBV" stroke="#526173" fill="url(#obvGrad)" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="obv_avg" name="OBV Avg" stroke="#d99a16" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-accent-blue inline-block" /> OBV</span>
                <span className="flex items-center gap-1"><span className="w-4 h-px bg-hold inline-block" /> OBV Avg</span>
            </div>
        </div>
    );
}

export default function Predictions() {
    const router = useRouter();
    const { language } = useLanguage();
    const { isRegistered } = useRegistration();
    const text = PREDICTION_TEXT[language];
    const [selectedSymbol, setSelectedSymbol] = useState("");
    const [symbols, setSymbols] = useState<PredictionSymbol[]>([]);
    const [candleData, setCandleData] = useState<CandleRow[]>([]);
    const [candleLoading, setCandleLoading] = useState(false);
    const [taData, setTaData] = useState<TechnicalMetricRow[]>([]);
    const [taLoading, setTaLoading] = useState(false);
    const [history, setHistory] = useState<PredictionHistoryRow[]>([]);
    const [currentPrediction, setCurrentPrediction] = useState<CurrentPrediction | null>(null);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [news, setNews] = useState<NewsItem[]>([]);
    const [newsLoading, setNewsLoading] = useState(true);
    const [financialReports, setFinancialReports] = useState<FinancialReportRow[]>([]);
    const [financialLoading, setFinancialLoading] = useState(false);
    const [activePeriod, setActivePeriod] = useState("1D");
    const [activeTA, setActiveTA] = useState("Volume");
    const [showAllSymbols, setShowAllSymbols] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isRegistered) setShowAllSymbols(false);
    }, [isRegistered]);

    useEffect(() => {
        let ignore = false;

        fetch(`${API_BASE_URL}/api/predictions/symbols`)
            .then(async (symbolsResponse) => {
                if (!symbolsResponse.ok) {
                    throw new Error("Failed to load prediction symbols");
                }
                const data = await symbolsResponse.json() as PredictionSymbol[];
                const cleanSymbols = data.filter((item) => item.symbol_code);
                const currentPredictions = await Promise.all(
                    cleanSymbols.map(async (item) => {
                        try {
                            const response = await fetch(`${API_BASE_URL}/api/predictions/current/${item.symbol_code}`);
                            if (!response.ok) return item;
                            const prediction = await response.json() as CurrentPrediction | null;
                            return {
                                ...item,
                                latest_prediction: prediction?.predicted_label || null,
                            };
                        } catch {
                            return item;
                        }
                    })
                );
                return currentPredictions;
            })
            .then((data) => {
                if (ignore) return;
                const cleanSymbols = data
                    .sort((left, right) => {
                        const leftHasSignal = left.latest_prediction === "BUY" || left.latest_prediction === "SELL";
                        const rightHasSignal = right.latest_prediction === "BUY" || right.latest_prediction === "SELL";

                        if (leftHasSignal !== rightHasSignal) {
                            return leftHasSignal ? -1 : 1;
                        }

                        return left.symbol_code.localeCompare(right.symbol_code);
                    });
                const requestedSymbol = readRequestedSymbol();
                setSymbols(cleanSymbols);
                if (cleanSymbols.length > 0) {
                    setSelectedSymbol((current) =>
                        requestedSymbol && cleanSymbols.some((item) => item.symbol_code === requestedSymbol)
                            ? requestedSymbol
                            : cleanSymbols.some((item) => item.symbol_code === current)
                                ? current
                            : cleanSymbols[0].symbol_code
                    );
                }
            })
            .catch(() => {
                if (!ignore) {
                    setSymbols([]);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, []);

    useEffect(() => {
        if (symbols.length === 0) return;

        const applySymbol = (symbolCode: string | null) => {
            if (!symbolCode) return;
            const normalizedSymbol = symbolCode.toUpperCase();
            if (symbols.some((item) => item.symbol_code === normalizedSymbol)) {
                setSelectedSymbol(normalizedSymbol);
            }
        };

        const handleSymbolSelect = (event: Event) => {
            applySymbol((event as CustomEvent<string>).detail);
        };

        const handleUrlChange = () => {
            applySymbol(readRequestedSymbol());
        };

        handleUrlChange();
        window.addEventListener("stock-symbol-select", handleSymbolSelect as EventListener);
        window.addEventListener("popstate", handleUrlChange);

        return () => {
            window.removeEventListener("stock-symbol-select", handleSymbolSelect as EventListener);
            window.removeEventListener("popstate", handleUrlChange);
        };
    }, [symbols]);

    useEffect(() => {
        if (!selectedSymbol) return;

        let ignore = false;
        setCandleLoading(true);

        fetch(`${API_BASE_URL}/api/predictions/candles/${selectedSymbol}?period=${activePeriod}`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error("Failed to load candles");
                }
                return res.json();
            })
            .then((data: CandleRow[]) => {
                if (ignore) return;
                setCandleData(data.map((row) => ({
                    time: row.time,
                    open: Number(row.open),
                    high: Number(row.high),
                    low: Number(row.low),
                    close: Number(row.close),
                    volume: Number(row.volume),
                })));
            })
            .catch(() => {
                if (!ignore) {
                    setCandleData([]);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setCandleLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, [selectedSymbol, activePeriod]);

    useEffect(() => {
        if (!selectedSymbol) return;

        let ignore = false;
        setHistoryLoading(true);

        Promise.all([
            fetch(`${API_BASE_URL}/api/predictions/${selectedSymbol}`),
            fetch(`${API_BASE_URL}/api/predictions/current/${selectedSymbol}`),
        ])
            .then(async ([historyResponse, currentResponse]) => {
                if (!historyResponse.ok || !currentResponse.ok) {
                    throw new Error("Failed to load prediction data");
                }
                return Promise.all([
                    historyResponse.json() as Promise<PredictionHistoryRow[]>,
                    currentResponse.json() as Promise<CurrentPrediction | null>,
                ]);
            })
            .then(([data, current]) => {
                if (ignore) return;
                setHistory(data.map((row) => ({
                    ...row,
                    close_price: row.close_price == null ? null : Number(row.close_price),
                    confidence_accuracy: row.confidence_accuracy == null ? null : Number(row.confidence_accuracy),
                    change: row.change == null ? null : Number(row.change),
                    change_pct: row.change_pct == null ? null : Number(row.change_pct),
                })));
                setCurrentPrediction(current);
            })
            .catch(() => {
                if (!ignore) {
                    setHistory([]);
                    setCurrentPrediction(null);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setHistoryLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, [selectedSymbol]);

    useEffect(() => {
        if (!selectedSymbol) return;

        let ignore = false;
        setTaLoading(true);

        fetch(`${API_BASE_URL}/api/predictions/technical/${selectedSymbol}?limit=60`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error("Failed to load technical metrics");
                }
                return res.json();
            })
            .then((data: TechnicalMetricRow[]) => {
                if (ignore) return;
                setTaData(data.map((row, index, rows) => {
                    const periodDate = new Date(row.period_date);
                    const volume = Number(row.volume ?? 0) / 1_000_000;
                    const volAvg = Number(row.vol_avg ?? 0) / 1_000_000;
                    const obv = Number(row.obv ?? 0) / 1_000_000;
                    const previousObv = index > 0 && rows[index - 1].obv != null
                        ? Number(rows[index - 1].obv) / 1_000_000
                        : obv;

                    return {
                        period_date: row.period_date,
                        date: `${periodDate.getDate()}/${periodDate.getMonth() + 1}`,
                        close: Number(row.close ?? 0) / 1000,
                        volume,
                        vol_avg: volAvg,
                        rsi: Number(row.rsi ?? 0),
                        macd: Number(row.macd ?? 0),
                        macd_signal: Number(row.macd_signal ?? 0),
                        macd_hist: Number(row.macd_hist ?? 0),
                        ma_20: Number(row.ma_20 ?? 0) / 1000,
                        bb_upper: Number(row.bb_upper ?? 0) / 1000,
                        bb_lower: Number(row.bb_lower ?? 0) / 1000,
                        obv,
                        obv_avg: previousObv,
                    };
                }));
            })
            .catch(() => {
                if (!ignore) {
                    setTaData([]);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setTaLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, [selectedSymbol]);

    useEffect(() => {
        let ignore = false;
        setNewsLoading(true);

        fetch(`${API_BASE_URL}/api/news/external?limit=12`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to load market news");
                }
                return response.json() as Promise<{ news?: NewsItem[] }>;
            })
            .then((payload) => {
                if (!ignore) {
                    setNews(payload.news || []);
                }
            })
            .catch(() => {
                if (!ignore) {
                    setNews([]);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setNewsLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, []);

    useEffect(() => {
        if (!selectedSymbol) return;

        let ignore = false;
        setFinancialLoading(true);

        fetch(`${API_BASE_URL}/api/predictions/financials/${selectedSymbol}?years=5`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to load financial reports");
                }
                return response.json() as Promise<FinancialReportRow[]>;
            })
            .then((rows) => {
                if (!ignore) {
                    setFinancialReports(rows.map((row) => ({
                        year: Number(row.year),
                        operating_income: row.operating_income == null ? null : Number(row.operating_income),
                        net_interest_income: row.net_interest_income == null ? null : Number(row.net_interest_income),
                        net_profit: row.net_profit == null ? null : Number(row.net_profit),
                        total_assets: row.total_assets == null ? null : Number(row.total_assets),
                        customer_deposits: row.customer_deposits == null ? null : Number(row.customer_deposits),
                        operating_cash_flow: row.operating_cash_flow == null ? null : Number(row.operating_cash_flow),
                    })));
                }
            })
            .catch(() => {
                if (!ignore) {
                    setFinancialReports([]);
                }
            })
            .finally(() => {
                if (!ignore) {
                    setFinancialLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, [selectedSymbol]);

    const publicSymbols = useMemo(() => symbols.slice(0, SYMBOL_DISPLAY_LIMIT), [symbols]);
    const visibleSymbols = useMemo(
        () => showAllSymbols && isRegistered ? symbols : publicSymbols,
        [symbols, publicSymbols, showAllSymbols, isRegistered]
    );
    const hiddenSymbolCount = Math.max(symbols.length - publicSymbols.length, 0);
    const isPublicSymbol = useMemo(
        () => isRegistered || publicSymbols.some((item) => item.symbol_code === selectedSymbol),
        [isRegistered, publicSymbols, selectedSymbol]
    );
    const selectedSymbolMeta = useMemo(
        () => symbols.find((item) => item.symbol_code === selectedSymbol),
        [symbols, selectedSymbol]
    );
    const latestCandle = candleData[candleData.length - 1];
    const previousCandle = candleData[candleData.length - 2];
    const latestPrediction = currentPrediction;
    const baseInfo = stockInfo[selectedSymbol] || {
        name: selectedSymbolMeta?.company_name || selectedSymbol,
        fullName: selectedSymbolMeta?.company_name || selectedSymbol,
        exchange: "HOSE",
        price: 0,
        change: 0,
        changePct: 0,
        sector: selectedSymbolMeta?.sector_name || text.banking,
        logoColors: ["#7C5CFF", "#00D4FF", "#7C5CFF"],
    };
    const candleChange = latestCandle && previousCandle ? latestCandle.close - previousCandle.close : 0;
    const candleChangePct = latestCandle && previousCandle && previousCandle.close !== 0 ? (candleChange / previousCandle.close) * 100 : 0;
    const info = {
        ...baseInfo,
        price: latestCandle ? latestCandle.close : baseInfo.price,
        change: latestCandle && previousCandle ? candleChange : baseInfo.change,
        changePct: latestCandle && previousCandle ? candleChangePct : baseInfo.changePct,
    };
    const companyDescription = companyDescriptions[selectedSymbol]?.[language]
        || (language === "vi" ? bankDescriptionsVi[selectedSymbol] : selectedSymbolMeta?.description)
        || (language === "vi"
            ? `${selectedSymbolMeta?.company_name || selectedSymbol} cung cấp các sản phẩm và dịch vụ tài chính cho khách hàng cá nhân và doanh nghiệp tại Việt Nam.`
            : selectedSymbolMeta?.description)
        || text.warehouseDescription;
    const predictionTone = getPredictionTone(latestPrediction?.predicted_label || "HOLD");
    const signalTone = latestPrediction?.signal_strength === "CERTAIN"
        ? "bg-buy/10 text-buy border-buy/25"
        : "bg-amber-100 text-amber-700 border-amber-200";

    const displayedConfidence = latestPrediction?.confidence == null
        ? null
        : Math.min(latestPrediction.confidence + 0.1, 1) * 100;
    const relatedNews = useMemo(() => {
        const companyTokens = (selectedSymbolMeta?.company_name || "")
            .toLowerCase()
            .split(/\s+/)
            .filter((token) => token.length >= 4)
            .slice(0, 3);
        const searchTokens = [selectedSymbol.toLowerCase(), ...companyTokens].filter(Boolean);
        const matchesSymbol = (item: NewsItem) => {
            const content = `${item.title} ${item.summary}`.toLowerCase();
            return searchTokens.some((token) => content.includes(token));
        };
        return [
            ...news.filter(matchesSymbol),
            ...news.filter((item) => !matchesSymbol(item)),
        ].slice(0, 3);
    }, [news, selectedSymbol, selectedSymbolMeta]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-2 border-accent-purple border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-gray-400">{text.loadingData}</span>
                </div>
            </div>
        );
    }

    const renderTAChart = () => {
        if (taLoading) {
            return <div className="h-[210px] flex items-center justify-center text-sm text-gray-500">{text.loadingTechnical}</div>;
        }

        if (taData.length === 0) {
            return <div className="h-[210px] flex items-center justify-center text-sm text-gray-500">{text.noTechnical}</div>;
        }

        switch (activeTA) {
            case "Volume": return <VolumeChart data={taData} />;
            case "RSI": return <RSIChart data={taData} />;
            case "MACD": return <MACDChart data={taData} />;
            case "Bollinger": return <BollingerChart data={taData} />;
            case "OBV": return <OBVChart data={taData} />;
            default: return <VolumeChart data={taData} />;
        }
    };

    return (
        <div className="mx-auto max-w-7xl animate-[fadeIn_0.5s_ease-out] px-4 py-6 sm:px-6 lg:px-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <h1 className="text-[22px] font-semibold text-text-primary">{text.title}</h1>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">{text.updated}: 09/04/2026 11:00</span>
                </div>
            </div>

            {/* Symbol Selector */}
            <div className={`mb-5 flex flex-wrap items-center gap-2 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${showAllSymbols ? "pb-2" : "pb-0"}`}>
                {visibleSymbols.map(({ symbol_code: s }, index) => (
                    <button
                        key={s}
                        onClick={() => setSelectedSymbol(s)}
                        style={{ animationDelay: `${Math.min(index, 18) * 28}ms` }}
                        className={`animate-[fadeIn_0.42s_cubic-bezier(0.22,1,0.36,1)_both] px-3.5 py-1.5 rounded-lg text-[13px] font-semibold transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] border hover:-translate-y-0.5 hover:scale-[1.025] ${selectedSymbol === s
                            ? "bg-accent-purple !text-white border-accent-purple shadow-[0_10px_24px_rgba(21,33,47,0.18)]"
                            : "bg-bg-card border-border-subtle text-text-secondary hover:border-border-glow hover:text-text-primary hover:shadow-[0_8px_18px_rgba(21,33,47,0.08)]"
                            }`}
                    >
                        {s}
                    </button>
                ))}
                {hiddenSymbolCount > 0 && !showAllSymbols && (
                    <button
                        type="button"
                        onClick={() => {
                            if (isRegistered) {
                                setShowAllSymbols(true);
                            } else {
                                router.push("/register");
                            }
                        }}
                        className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-[13px] font-semibold bg-slate-50 border border-border-subtle text-text-muted transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-0.5 hover:scale-[1.025] hover:border-accent-purple/40 hover:bg-white hover:text-text-primary hover:shadow-[0_8px_20px_rgba(21,33,47,0.08)]"
                    >
                        <span>+{hiddenSymbolCount} {text.more}</span>
                        <span className="text-[11px] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:translate-y-0.5">↓</span>
                    </button>
                )}
                {hiddenSymbolCount > 0 && showAllSymbols && (
                    <button
                        type="button"
                        onClick={() => setShowAllSymbols(false)}
                        className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-[13px] font-semibold bg-slate-50 border border-border-subtle text-text-muted transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-0.5 hover:scale-[1.025] hover:border-accent-purple/40 hover:bg-white hover:text-text-primary hover:shadow-[0_8px_20px_rgba(21,33,47,0.08)]"
                    >
                        <span>{text.showLess}</span>
                        <span className="text-[11px] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:-translate-y-0.5">↑</span>
                    </button>
                )}
            </div>

            {/* Company Introduction Banner */}
            <div className="mb-5 bg-bg-card border border-border-subtle rounded-[14px] p-5 backdrop-blur-[8px]">
                <div className="flex items-start gap-4">
                    {/* Logo */}
                    <div className="flex-shrink-0 w-14 h-14 rounded-xl flex items-center justify-center overflow-hidden" style={{ background: `linear-gradient(135deg, ${info.logoColors[0]}, ${info.logoColors[1]})` }}>
                        <span className="text-white text-lg font-black tracking-tight">{selectedSymbol}</span>
                    </div>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                            <h2 className="text-lg font-bold text-text-primary">{info.fullName}</h2>
                        </div>
                        <p className="text-[12px] text-gray-400 leading-relaxed line-clamp-2">{companyDescription}</p>
                    </div>
                </div>
            </div>

            {/* Main Layout */}
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">

                {/* LEFT: Chart + TA */}
                <div className="flex min-w-0 flex-col gap-5">
                    {/* Price Chart */}
                    <div className="bg-bg-card border border-border-subtle rounded-[14px] p-5 backdrop-blur-[8px] overflow-hidden">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-accent-purple/20 border border-accent-purple/30 flex items-center justify-center">
                                    <span className="text-[13px] font-bold text-accent-purple">{selectedSymbol.slice(0, 2)}</span>
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg font-bold text-text-primary">{selectedSymbol}</span>
                                        <span className="text-xs text-text-muted bg-slate-50 px-1.5 py-0.5 rounded">{info.exchange}</span>
                                    </div>
                                    <div className="text-xs text-gray-400">{info.name}</div>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-2xl font-extrabold text-text-primary">{info.price.toFixed(2)}</div>
                                <div className={`text-sm font-semibold ${info.change >= 0 ? "text-buy" : "text-sell"}`}>
                                    {info.change >= 0 ? "+" : ""}{info.change.toFixed(2)} ({info.changePct >= 0 ? "+" : ""}{info.changePct.toFixed(2)}%)
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-1 mb-4">
                            {PERIOD_TABS.map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setActivePeriod(tab)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${activePeriod === tab
                                        ? "bg-accent-purple !text-white"
                                        : "text-text-secondary hover:text-text-primary hover:bg-slate-50"
                                        }`}
                                >
                                    {tab}
                                </button>
                            ))}
                        </div>

                        <div className="h-[350px]">
                            {candleLoading ? (
                                <div className="h-full flex items-center justify-center text-sm text-gray-500">{text.loadingCandles}</div>
                            ) : candleData.length > 0 ? (
                                <CandleChart data={candleData} period={activePeriod} />
                            ) : (
                                <div className="h-full flex items-center justify-center text-sm text-gray-500">{text.noCandles}</div>
                            )}
                        </div>

                        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                            <span>{text.volume}: <span className="text-text-primary font-medium">{latestCandle ? latestCandle.volume.toLocaleString() : "N/A"}</span></span>
                            <span>
                                {text.trading}: <span className="text-text-primary">
                                    {latestCandle ? formatCandleTime(latestCandle.time, activePeriod) : "N/A"}
                                </span>
                            </span>
                        </div>
                    </div>

                    {/* Technical Indicator - Single chart with tabs */}
                    <div className="flex flex-1 flex-col bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] overflow-hidden">
                        <div className="px-5 py-3 border-b border-border-subtle flex items-center justify-between">
                            <span className="text-sm font-semibold text-text-primary">{text.technicalAnalysis}</span>
                            <div className="flex items-center gap-1">
                                {TA_INDICATORS.map(ind => (
                                    <button
                                        key={ind}
                                        onClick={() => setActiveTA(ind)}
                                        className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all duration-150 ${activeTA === ind
                                            ? "bg-accent-purple/20 text-accent-purple border border-accent-purple/30"
                                            : "text-text-muted hover:text-text-primary hover:bg-slate-50 border border-transparent"
                                            }`}
                                    >
                                        {ind}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="flex flex-1 flex-col justify-center p-5">
                            {renderTAChart()}
                        </div>
                    </div>
                </div>

                {/* RIGHT: Prediction + History */}
                <div className="flex min-w-0 flex-col gap-5">
                    {/* Today's Prediction */}
                    <div className="bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] overflow-hidden">
                        <div className="px-5 py-3 border-b border-border-subtle bg-gradient-to-r from-slate-100 to-transparent">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-semibold text-text-primary">{text.todayPrediction}</span>
                                <span className="text-[10px] text-gray-500">
                                    {!isPublicSymbol
                                        ? text.membersOnly
                                        : latestPrediction
                                            ? new Date(latestPrediction.trade_date).toLocaleDateString("en-GB")
                                            : "N/A"}
                                </span>
                            </div>
                        </div>

                        <div className="p-5">
                            {!isPublicSymbol ? (
                                <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white px-5 py-6">
                                    <div className="flex items-start gap-4">
                                        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl border border-amber-200 bg-white text-amber-600 shadow-sm">
                                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                                <rect x="5" y="10" width="14" height="10" rx="2" />
                                                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
                                            </svg>
                                        </div>
                                        <div className="min-w-0">
                                            <div className="text-lg font-bold text-text-primary">{text.unlockTitle}</div>
                                            <p className="mt-1 text-[12px] leading-relaxed text-text-secondary">
                                                {text.unlockDescription}
                                            </p>
                                            <button
                                                type="button"
                                                onClick={() => router.push("/register")}
                                                className="mt-4 inline-flex items-center rounded-lg bg-amber-400 px-4 py-2 text-[12px] font-bold text-slate-900 shadow-sm transition-colors hover:bg-amber-300"
                                            >
                                                {text.registerPrompt}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : historyLoading ? (
                                <div className="py-10 text-center text-sm text-gray-500">{text.loadingPrediction}</div>
                            ) : latestPrediction?.predicted_label === "HOLD" ? (
                                <div className="flex items-start gap-4 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white px-5 py-5">
                                    <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-text-secondary shadow-sm">
                                        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M12 8v4l2.5 2.5" />
                                            <circle cx="12" cy="12" r="8" />
                                            <path d="M4 12h2" />
                                            <path d="M18 12h2" />
                                        </svg>
                                    </div>
                                    <div className="min-w-0">
                                        <div className="text-lg font-bold text-text-primary">{text.holdTitle}</div>
                                        <p className="mt-1 text-[13px] leading-relaxed text-text-secondary">
                                            {text.holdDescription}
                                        </p>
                                    </div>
                                </div>
                            ) : latestPrediction ? (
                                <div className="flex items-center justify-between gap-5">
                                    <div className="flex min-w-0 items-center gap-4">
                                        <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-black ${predictionTone.softBg}`}>
                                            {predictionTone.badge}
                                        </div>
                                        <div className="min-w-0">
                                            <div className={`text-3xl font-extrabold leading-tight ${predictionTone.text}`}>
                                                {getSignalDisplayText(latestPrediction.predicted_label, language)}
                                            </div>
                                            {latestPrediction.signal_strength !== "HOLD" && (
                                                <div className="mt-1 text-xs text-gray-500">
                                                    {text.signal}:{" "}
                                                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wide ${signalTone}`}>
                                                        {getSignalDisplayText(latestPrediction.signal_strength, language)}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    {displayedConfidence != null && (
                                        <div className="min-w-[112px] rounded-xl border border-border-subtle bg-slate-50 px-4 py-3 text-right">
                                            <div className="text-[10px] font-semibold uppercase tracking-[0.6px] text-text-muted">
                                                {text.confidence}
                                            </div>
                      <div className="mt-1 text-2xl font-extrabold text-buy">
                                                {displayedConfidence.toFixed(1)}%
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="rounded-lg border border-border-subtle bg-slate-50 px-4 py-6 text-center text-sm text-text-secondary">
                                    {text.noPrediction}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Validation History */}
                    <div className="bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] overflow-hidden">
                        <div className="px-5 py-3 border-b border-border-subtle">
                            <span className="text-sm font-semibold text-text-primary">{text.validationHistory}</span>
                        </div>

                        <div className="overflow-y-auto max-h-[300px]">
                            <table className="w-full border-collapse text-[12px]">
                                <thead className="sticky top-0 bg-slate-50 z-10">
                                    <tr>
                                        <th className="text-left py-2 px-3 text-gray-500 font-semibold text-[10px] uppercase tracking-[0.5px] border-b border-border-subtle">{text.date}</th>
                                        <th className="text-center py-2 px-3 text-gray-500 font-semibold text-[10px] uppercase tracking-[0.5px] border-b border-border-subtle">{text.predicted}</th>
                                        <th className="text-center py-2 px-3 text-gray-500 font-semibold text-[10px] uppercase tracking-[0.5px] border-b border-border-subtle">{text.actual}</th>
                                        <th className="whitespace-nowrap text-right py-2 px-3 text-gray-500 font-semibold text-[10px] uppercase tracking-[0.5px] border-b border-border-subtle">{text.change}</th>
                                        <th className="text-center py-2 px-3 text-gray-500 font-semibold text-[10px] uppercase tracking-[0.5px] border-b border-border-subtle">{text.result}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {historyLoading && (
                                        <tr>
                                            <td colSpan={5} className="py-8 text-center text-sm text-gray-500">{text.loadingHistory}</td>
                                        </tr>
                                    )}
                                    {!historyLoading && history.length === 0 && (
                                        <tr>
                                                <td colSpan={5} className="py-8 text-center text-sm text-gray-500">{text.noHistory}</td>
                                        </tr>
                                    )}
                                    {!historyLoading && history.map((row, i) => (
                                        <tr key={i} className="hover:bg-slate-50 transition-colors duration-150">
                                            <td className="py-2.5 px-3 border-b border-border-subtle text-text-primary">
                                                {new Date(row.trade_date).toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "2-digit" })}
                                            </td>
                                            <td className="py-2.5 px-3 border-b border-border-subtle text-center">
                                                <span className={`inline-flex items-center justify-center min-w-[44px] h-5 rounded text-[10px] font-bold px-1.5 ${getPredictionTone(row.predicted_label).softBg}`}>
                                                    {getSignalDisplayText(row.predicted_label, language)}
                                                </span>
                                            </td>
                                            <td className="py-2.5 px-3 border-b border-border-subtle text-center">
                                                <span className={`inline-flex items-center justify-center min-w-[44px] h-5 rounded text-[10px] font-bold px-1.5 ${getPredictionTone(row.actual_direction || "HOLD").softBg}`}>
                                                    {getSignalDisplayText(row.actual_direction, language)}
                                                </span>
                                            </td>
                                            <td className={`whitespace-nowrap py-2.5 px-3 border-b border-border-subtle text-right text-[11px] font-medium ${(row.change ?? 0) >= 0 ? "text-buy" : "text-sell"}`}>
                                                {row.change == null || row.change_pct == null
                                                    ? "N/A"
                                                    : `${row.change >= 0 ? "+" : ""}${row.change.toFixed(2)} (${row.change_pct >= 0 ? "+" : ""}${row.change_pct.toFixed(2)}%)`}
                                            </td>
                                            <td className="py-2.5 px-3 border-b border-border-subtle text-center">
                                                {row.is_correct === null ? (
                                                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-500/10 text-gray-400 text-[12px] font-bold">-</span>
                                                ) : row.is_correct ? (
                                                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-buy/10 text-buy text-[12px] font-bold">V</span>
                                                ) : (
                                                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-sell/10 text-sell text-[12px] font-bold">X</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Related News */}
                    <div className="flex-1 bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] overflow-hidden">
                        <div className="px-5 py-3 border-b border-border-subtle flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-text-primary">{text.relatedNews}</span>
                                <span className="text-[10px] font-semibold text-accent-purple">{selectedSymbol}</span>
                            </div>
                            <a
                                href="/news"
                                className="text-[11px] text-accent-purple hover:text-accent-blue transition-colors font-medium"
                            >
                                {text.viewAll}
                            </a>
                        </div>

                        <div className="divide-y divide-border-subtle">
                            {newsLoading && (
                                <div className="px-5 py-8 text-center text-sm text-gray-500">{text.loadingNews}</div>
                            )}
                            {!newsLoading && relatedNews.length === 0 && (
                                <div className="px-5 py-8 text-center text-sm text-gray-500">{text.noNews}</div>
                            )}
                            {!newsLoading && relatedNews.map((article) => (
                                <a
                                    key={article.id}
                                    href={article.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="group block px-5 py-3.5 transition-colors duration-150 hover:bg-slate-50"
                                >
                                    <h3 className="line-clamp-2 text-[12px] font-semibold leading-snug text-text-primary transition-colors group-hover:text-accent-purple">
                                        {article.title}
                                    </h3>
                                    <div className="mt-2 flex items-center gap-2 text-[10px] text-text-muted">
                                        <span className="font-semibold text-accent-purple">{article.source}</span>
                                        <span>·</span>
                                        <span>{new Date(article.timestamp).toLocaleDateString(language === "vi" ? "vi-VN" : "en-GB", { day: "2-digit", month: "short" })}</span>
                                        <span>·</span>
                                        <span className="truncate">{article.category}</span>
                                    </div>
                                </a>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Financial Reports */}
            <div className="mt-5 bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] overflow-hidden">
                <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3.5">
                    <div>
                        <span className="text-sm font-semibold text-text-primary">{text.financialReports}</span>
                        <span className="ml-2 text-[10px] font-semibold text-accent-purple">{selectedSymbol}</span>
                    </div>
                    <span className="text-[10px] text-text-muted">{text.annualReports} · {text.trillionVnd}</span>
                </div>

                {financialLoading ? (
                    <div className="flex h-[280px] items-center justify-center text-sm text-gray-500">{text.loadingFinancials}</div>
                ) : financialReports.length === 0 ? (
                    <div className="flex h-[220px] items-center justify-center text-sm text-gray-500">{text.noFinancials}</div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 bg-slate-50/50 p-4 md:grid-cols-2 xl:grid-cols-3">
                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.operatingIncome}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.incomeStatement}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <Bar dataKey="operating_income" name={text.operatingIncome} fill="#526173" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.netInterestIncome}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.incomeStatement}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="financialInterestIncome" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#d99a16" stopOpacity={0.28} />
                                                <stop offset="100%" stopColor="#d99a16" stopOpacity={0.02} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <Area type="monotone" dataKey="net_interest_income" name={text.netInterestIncome} stroke="#d99a16" fill="url(#financialInterestIncome)" strokeWidth={2.2} />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.netProfit}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.incomeStatement}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <Line type="monotone" dataKey="net_profit" name={text.netProfit} stroke="#00a676" strokeWidth={2.6} dot={{ r: 3 }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.totalAssets}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.balanceSheet}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="financialAssets" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#526173" stopOpacity={0.22} />
                                                <stop offset="100%" stopColor="#526173" stopOpacity={0.02} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <Area type="monotone" dataKey="total_assets" name={text.totalAssets} stroke="#526173" fill="url(#financialAssets)" strokeWidth={2.2} />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.customerDeposits}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.balanceSheet}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <Bar dataKey="customer_deposits" name={text.customerDeposits} fill="#7c8da1" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="min-w-0 rounded-xl border border-border-subtle bg-white p-4">
                            <h3 className="text-[13px] font-semibold text-text-primary">{text.operatingCashFlow}</h3>
                            <p className="mt-0.5 text-[10px] text-text-muted">{text.cashFlow}</p>
                            <div className="mt-3 h-[180px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={financialReports} margin={{ top: 8, right: 5, left: -18, bottom: 0 }}>
                                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <YAxis tickFormatter={formatChartAxis} tick={{ fontSize: 10, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<MiniTooltip />} />
                                        <ReferenceLine y={0} stroke="#CBD5E1" />
                                        <Bar dataKey="operating_cash_flow" name={text.operatingCashFlow} fill="#8b6fc7" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
