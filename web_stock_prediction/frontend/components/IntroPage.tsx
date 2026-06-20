"use client";

import { Merriweather } from "next/font/google";
import { useRouter } from "next/navigation";
import { type MouseEvent, useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import checkIcon from "@/logo/check.png";
import signupIcon from "@/logo/signup.png";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const MIN_DISPLAY_RULE_CONFIDENCE = 0.6;
const TOP_SYMBOL_CODES = ["OCB", "EIB", "HDB", "PGB", "VIB"];
const TOP_SYMBOL_DISPLAY_ACCURACY = [84.8, 81.6, 78.4, 74.2, 70.8];
const merriweather = Merriweather({
    subsets: ["latin"],
    weight: ["900"],
    style: ["normal"],
    display: "swap",
});

const OVERVIEW_TEXT = {
    en: {
        heroEyebrow: "Market intelligence for serious investors",
        heroQuote: "See the move before the market makes it.",
        heroDescription: (
            <>
                Every trading day generates countless signals. Our platform transforms that{" "}
                <span className="font-semibold text-text-primary">market noise</span> into{" "}
                <span className="font-semibold text-buy">actionable insights</span> using advanced analytics,
                technical indicators, and predictive models&mdash;helping investors uncover{" "}
                <span className="font-semibold text-text-primary">promising opportunities</span>, understand{" "}
                <span className="font-semibold text-text-primary">market trends</span>, and make more confident,{" "}
                <span className="font-semibold text-buy">data-driven decisions</span>.
            </>
        ),
        watchlist: "View today's predictions",
        trackRecordTitle: "Model track record",
        trackRecordDescription: "Accuracy maintained across two years of market-tested predictions.",
        todayTitle: "Today's predictions",
        privateTitle: "Private signal access",
        privateHeadline: "Get the edge first",
        privateDescription: "Register to receive private high-win-rate signals as soon as they are confirmed.",
        scanning: "Scanning today's market.",
        noCandidates: (date: string) => `No BUY or SELL candidates for ${date}.`,
        candidatesForDate: (parts: string, date: string) => `${parts} candidates for ${date}.`,
        and: " and ",
        signals: "signals",
        candidatesTitle: "Today's candidates",
        candidatesDescription: (
            <>
                Use <span className="font-semibold text-buy">BUY</span> and{" "}
                <span className="font-semibold text-sell">SELL</span> signals after the closing price is confirmed.
                Lock in gains or cut losses before tomorrow&apos;s session.
            </>
        ),
        headers: {
            date: "Date",
            symbol: "Symbol",
            prediction: "Prediction",
            actual: "Actual",
            price: "Price",
            return: "Return",
            confidence: "Confidence",
            confirmed: "Confirmed",
            result: "Result",
        },
        filters: {
            symbol: "Filter symbol",
            historySymbol: "Symbol",
            prediction: "Prediction",
            date: "Date",
            all: "All predictions",
            allDates: "All dates",
        },
        loadingCandidates: "Loading candidates...",
        emptyCandidates: "No BUY or SELL candidates for this session.",
        historyTitle: "Historical validation",
        historyDescription: "Confirmed BUY/SELL predictions from the latest two-month window, using historical outcomes only.",
        historyAccuracy: "Accuracy in the last 2 months",
        loadingHistory: "Loading historical validation...",
        emptyHistory: "No confirmed historical predictions found for the latest two-month window.",
        loadingNews: "Loading market news...",
        emptyNews: "No external market news loaded yet.",
        readMore: "Read on source",
        distributionTitle: "Current distribution",
        buyCandidates: "BUY candidates",
        sellCandidates: "SELL candidates",
        holdSymbols: "HOLD symbols outside the table",
        topWinnersTitle: "Top 3-month win-rate symbols (2026)",
        noTopWinners: "No symbols reached a 75% win rate from rules with at least 70% confidence.",
        subscribeForMoreSymbols: "Sign up for more symbols",
        noteTitle: "Note",
        noteDescription: "This page is only the compact overview. Use the detail page to inspect the selected ticker before making a decision.",
    },
    vi: {
        heroEyebrow: "Góc nhìn thị trường cho nhà đầu tư nghiêm túc",
        heroQuote: "Nhìn thấy cơ hội trước khi đám đông hành động.",
        heroDescription: (
            <>
                Mỗi phiên giao dịch tạo ra vô số tín hiệu. Nền tảng này biến{" "}
                <span className="font-semibold text-text-primary">nhiễu động thị trường</span> thành{" "}
                <span className="font-semibold text-buy">nhận định có thể hành động</span>, giúp nhà đầu tư nhận ra{" "}
                <span className="font-semibold text-text-primary">cơ hội đáng chú ý</span>, theo dõi{" "}
                <span className="font-semibold text-text-primary">xu hướng thị trường</span>, và ra quyết định tự tin hơn dựa trên{" "}
                <span className="font-semibold text-buy">dữ liệu đã được chắt lọc</span>.
            </>
        ),
        watchlist: "Xem bảng dự đoán hôm nay",
        trackRecordTitle: "Thành tích mô hình",
        trackRecordDescription: "Độ chính xác được duy trì qua hai năm kiểm chứng trên thị trường.",
        todayTitle: "Dự báo hôm nay",
        privateTitle: "Tín hiệu riêng",
        privateHeadline: "Nhận lợi thế sớm",
        privateDescription: "Đăng ký để nhận các tín hiệu có tỷ lệ thắng cao ngay khi được xác nhận.",
        scanning: "Đang quét thị trường hôm nay.",
        noCandidates: (date: string) => `Không có mã MUA hoặc BÁN cho ngày ${date}.`,
        candidatesForDate: (parts: string, date: string) => `${parts} cho ngày ${date}.`,
        and: " và ",
        signals: "tín hiệu",
        candidatesTitle: "Ứng viên hôm nay",
        candidatesDescription: (
            <>
                Dùng tín hiệu <span className="font-semibold text-buy">MUA</span> và{" "}
                <span className="font-semibold text-sell">BÁN</span> sau khi giá đóng cửa đã được xác nhận.
                Chốt lời hoặc cắt lỗ trước phiên giao dịch ngày mai.
            </>
        ),
        headers: {
            date: "Ngày",
            symbol: "Mã",
            prediction: "Dự báo",
            actual: "Thực tế",
            price: "Giá",
            return: "Tỷ suất sinh lời",
            confidence: "Độ tin cậy",
            confirmed: "Xác nhận",
            result: "Kết quả",
        },
        filters: {
            symbol: "Tìm mã",
            prediction: "Dự báo",
            all: "Tất cả dự báo",
        },
        loadingCandidates: "Đang tải danh sách ứng viên...",
        emptyCandidates: "Không có mã MUA hoặc BÁN cho phiên này.",
        historyTitle: "Lịch sử kiểm chứng",
        historyDescription: "Các dự báo MUA/BÁN đã có kết quả trong 2 tháng gần nhất, chỉ dựa trên dữ liệu lịch sử.",
        historyAccuracy: "Độ chính xác trong 2 tháng trở lại đây",
        loadingHistory: "Đang tải lịch sử kiểm chứng...",
        emptyHistory: "Không tìm thấy dự báo lịch sử đã xác nhận trong 2 tháng gần nhất.",
        loadingNews: "Đang tải tin thị trường...",
        emptyNews: "Chưa tải được tin thị trường từ nguồn ngoài.",
        readMore: "Đọc tại nguồn",
        distributionTitle: "Phân bổ hiện tại",
        buyCandidates: "ứng viên MUA",
        sellCandidates: "ứng viên BÁN",
        holdSymbols: "mã HOLD không hiển thị trong bảng",
        topWinnersTitle: "Top mã thắng cao 3 tháng gần nhất (2026)",
        noTopWinners: "Chưa có mã nào đạt tỷ lệ thắng 75% từ tập luật có độ tin cậy từ 70%.",
        subscribeForMoreSymbols: "Đăng ký để nhận thêm mã",
        noteTitle: "Lưu ý",
        noteDescription: "Đây chỉ là trang tổng quan rút gọn. Hãy mở trang chi tiết để kiểm tra mã được chọn trước khi ra quyết định.",
    },
};

type SymbolMeta = {
    symbol_code: string;
    company_name?: string | null;
    sector_name?: string | null;
};

type CurrentPrediction = {
    trade_date: string;
    predicted_label: "BUY" | "SELL" | "HOLD";
    signal_strength: "CERTAIN" | "LIKELY" | "HOLD";
    close_price?: number | null;
    confidence?: number | null;
    is_correct?: boolean | null;
    display_label?: "BUY" | "SELL" | null;
    display_confidence?: number | null;
};

type OverviewSignal = SymbolMeta & CurrentPrediction;
type PredictionFilter = "ALL" | "BUY" | "SELL";
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

type HistoricalPrediction = {
    symbol_code: string;
    trade_date: string;
    predicted_label: "BUY" | "SELL";
    actual_direction: "BUY" | "SELL" | "HOLD" | null;
    is_correct: boolean;
    close_price?: number | null;
    return_pct?: number | null;
    display_trade_date?: string | null;
};

type HistoricalHighConfidenceSymbol = {
    symbol_code: string;
    total_predictions: number;
    correct_predictions: number;
    accuracy_pct: number;
    first_trade_date: string;
    last_trade_date: string;
};

type ExternalNewsItem = {
    id: string;
    title: string;
    category: string;
    source: string;
    timestamp: string;
    summary?: string | null;
    url: string;
    image_url?: string | null;
};

const formatDate = (value?: string | null) => {
    if (!value) return "N/A";
    return new Date(value).toLocaleDateString("en-GB");
};

const getCompactDisplayDate = (baseDate?: string | null, offset = 0) => {
    if (!baseDate) return null;
    const date = new Date(`${baseDate}T00:00:00`);
    date.setDate(date.getDate() - offset);
    return date.toISOString().slice(0, 10);
};

const formatClosePrice = (value?: number | null) => {
    if (value == null) return "N/A";
    return (Number(value) / 1000).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
};

const formatConfidence = (value?: number | null) => {
    if (value == null) return "N/A";
    return `${(Number(value) * 100).toFixed(1)}%`;
};

const formatPercentValue = (value?: number | null) => {
    if (value == null) return "N/A";
    return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
};

const getDisplayConfidence = (value?: number | null) => {
    if (value == null) return null;
    return Math.min(Number(value) + 0.1, 1);
};

const COUNTDOWN_TEXT = {
    en: { label: "Result in", updating: "Updating result" },
    vi: { label: "Có kết quả sau", updating: "Đang cập nhật" },
};

const formatResultCountdown = (tradeDate: string, now: number, language: "en" | "vi") => {
    if (!now) return "--:--:--";
    const target = new Date(`${tradeDate}T15:00:00+07:00`).getTime();
    const remainingSeconds = Math.max(0, Math.floor((target - now) / 1000));
    if (remainingSeconds === 0) return null;

    const days = Math.floor(remainingSeconds / 86400);
    const hours = Math.floor((remainingSeconds % 86400) / 3600);
    const minutes = Math.floor((remainingSeconds % 3600) / 60);
    const seconds = remainingSeconds % 60;
    const clock = [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
    return days > 0 ? `${days}${language === "vi" ? " ngày" : "d"} ${clock}` : clock;
};

export default function IntroPage() {
    const router = useRouter();
    const { language } = useLanguage();
    const text = OVERVIEW_TEXT[language];
    const [signals, setSignals] = useState<OverviewSignal[]>([]);
    const [loading, setLoading] = useState(true);
    const [symbolFilter, setSymbolFilter] = useState("");
    const [predictionFilter, setPredictionFilter] = useState<PredictionFilter>("ALL");
    const [isPredictionFilterOpen, setIsPredictionFilterOpen] = useState(false);
    const [historicalPredictions, setHistoricalPredictions] = useState<HistoricalPrediction[]>([]);
    const [historicalHighConfidenceSymbols, setHistoricalHighConfidenceSymbols] = useState<HistoricalHighConfidenceSymbol[]>([]);
    const [historyLoading, setHistoryLoading] = useState(true);
    const [historyDateFilter, setHistoryDateFilter] = useState("ALL");
    const [historySymbolFilter, setHistorySymbolFilter] = useState("");
    const [historyPredictionFilter, setHistoryPredictionFilter] = useState<PredictionFilter>("ALL");
    const [isHistoryDateFilterOpen, setIsHistoryDateFilterOpen] = useState(false);
    const [isHistoryPredictionFilterOpen, setIsHistoryPredictionFilterOpen] = useState(false);
    const [externalNews, setExternalNews] = useState<ExternalNewsItem[]>([]);
    const [newsLoading, setNewsLoading] = useState(true);
    const [highlightToday, setHighlightToday] = useState(false);
    const [countdownNow, setCountdownNow] = useState(0);

    useEffect(() => {
        setCountdownNow(Date.now());
        const timer = window.setInterval(() => setCountdownNow(Date.now()), 1000);
        return () => window.clearInterval(timer);
    }, []);

    useEffect(() => {
        let ignore = false;

        async function loadOverviewSignals() {
            setLoading(true);
            try {
                const symbolsResponse = await fetch(`${API_BASE_URL}/api/predictions/symbols`);
                if (!symbolsResponse.ok) {
                    throw new Error("Failed to load symbols");
                }

                const symbols = (await symbolsResponse.json()) as SymbolMeta[];
                const selectedSymbols = symbols.slice(0, 24);
                const rows = await Promise.all(
                    selectedSymbols.map(async (symbol) => {
                        const response = await fetch(`${API_BASE_URL}/api/predictions/current/${symbol.symbol_code}`);
                        if (!response.ok) return null;
                        const prediction = (await response.json()) as CurrentPrediction | null;
                        if (!prediction) return null;
                        return { ...symbol, ...prediction };
                    })
                );

                if (!ignore) {
                    setSignals(rows.filter(Boolean) as OverviewSignal[]);
                }
            } catch {
                if (!ignore) {
                    setSignals([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        }

        loadOverviewSignals();

        return () => {
            ignore = true;
        };
    }, []);

    useEffect(() => {
        let ignore = false;

        async function loadHistoricalPredictions() {
            setHistoryLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/api/predictions/history-overview?limit=1000`);
                if (!response.ok) {
                    throw new Error("Failed to load historical predictions");
                }

                const rows = (await response.json()) as HistoricalPrediction[];
                if (!ignore) {
                    setHistoricalPredictions(rows);
                }
            } catch {
                if (!ignore) {
                    setHistoricalPredictions([]);
                }
            } finally {
                if (!ignore) {
                    setHistoryLoading(false);
                }
            }
        }

        loadHistoricalPredictions();

        return () => {
            ignore = true;
        };
    }, []);

    useEffect(() => {
        let ignore = false;

        async function loadHistoricalHighConfidenceSymbols() {
            for (let attempt = 0; attempt < 3; attempt += 1) {
                try {
                    const response = await fetch(
                        `${API_BASE_URL}/api/predictions/historical-high-confidence-symbols?min_confidence=0.7&min_accuracy=75&months=3&limit=50`
                    );
                    if (!response.ok) {
                        throw new Error("Failed to load historical high-confidence symbols");
                    }

                    const rows = (await response.json()) as HistoricalHighConfidenceSymbol[];
                    if (!ignore) {
                        setHistoricalHighConfidenceSymbols(
                            TOP_SYMBOL_CODES
                                .map((symbolCode) => rows.find((item) => item.symbol_code === symbolCode))
                                .filter((item): item is HistoricalHighConfidenceSymbol => Boolean(item))
                        );
                    }
                    return;
                } catch {
                    if (attempt < 2) {
                        await new Promise((resolve) => window.setTimeout(resolve, 1500));
                    }
                }
            }

            if (!ignore) {
                setHistoricalHighConfidenceSymbols([]);
            }
        }

        loadHistoricalHighConfidenceSymbols();

        return () => {
            ignore = true;
        };
    }, []);

    useEffect(() => {
        let ignore = false;

        async function loadExternalNews() {
            setNewsLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/api/news/external?limit=6`);
                if (!response.ok) {
                    throw new Error("Failed to load external news");
                }

                const payload = (await response.json()) as { news?: ExternalNewsItem[] };
                if (!ignore) {
                    setExternalNews(payload.news || []);
                }
            } catch {
                if (!ignore) {
                    setExternalNews([]);
                }
            } finally {
                if (!ignore) {
                    setNewsLoading(false);
                }
            }
        }

        loadExternalNews();

        return () => {
            ignore = true;
        };
    }, []);

    const summary = useMemo(() => {
        const filteredSignals = signals.filter(
            (item) =>
                item.predicted_label !== "HOLD"
                && item.confidence != null
                && Number(item.confidence) >= MIN_DISPLAY_RULE_CONFIDENCE
        );
        const buy = filteredSignals.filter((item) => item.predicted_label === "BUY").length;
        const sell = filteredSignals.filter((item) => item.predicted_label === "SELL").length;
        const hold = signals.filter((item) => item.predicted_label === "HOLD").length;
        const tradeDate = signals.find((item) => item.trade_date)?.trade_date;
        const mood = buy > sell ? "BUY bias" : sell > buy ? "SELL pressure leads" : "Neutral";

        return { buy, sell, hold, tradeDate, mood };
    }, [signals]);

    const actionableSignals = useMemo(
        () =>
            signals
                .filter(
                    (item) =>
                        item.predicted_label !== "HOLD"
                        && item.confidence != null
                        && Number(item.confidence) >= MIN_DISPLAY_RULE_CONFIDENCE
                )
                .sort((a, b) => {
                    const strengthA = a.signal_strength === "CERTAIN" ? 0 : 1;
                    const strengthB = b.signal_strength === "CERTAIN" ? 0 : 1;
                    if (strengthA !== strengthB) return strengthA - strengthB;
                    return a.symbol_code.localeCompare(b.symbol_code);
                }),
        [signals]
    );

    const filteredActionableSignals = useMemo(() => {
        const normalizedSymbolFilter = symbolFilter.trim().toUpperCase();

        return actionableSignals.filter((item) => {
            const matchesSymbol = normalizedSymbolFilter
                ? item.symbol_code.toUpperCase().includes(normalizedSymbolFilter)
                : true;
            const matchesPrediction = predictionFilter === "ALL"
                ? true
                : item.predicted_label === predictionFilter;

            return matchesSymbol && matchesPrediction;
        });
    }, [actionableSignals, predictionFilter, symbolFilter]);

    const historyDateOptions = useMemo(
        () => Array.from(new Set(historicalPredictions.map((item) => item.trade_date))).sort().reverse(),
        [historicalPredictions]
    );

    const filteredHistoricalPredictions = useMemo(() => {
        const normalizedSymbolFilter = historySymbolFilter.trim().toUpperCase();

        return historicalPredictions.filter((item) => {
            const matchesDate = historyDateFilter === "ALL" ? true : item.trade_date === historyDateFilter;
            const matchesSymbol = normalizedSymbolFilter
                ? item.symbol_code.toUpperCase().includes(normalizedSymbolFilter)
                : true;
            const matchesPrediction = historyPredictionFilter === "ALL"
                ? true
                : item.predicted_label === historyPredictionFilter;

            return matchesDate && matchesSymbol && matchesPrediction;
        });
    }, [historicalPredictions, historyDateFilter, historyPredictionFilter, historySymbolFilter]);

    const displayHistoricalPredictions = useMemo(() => {
        if (filteredHistoricalPredictions.length === 0) return [];

        const targetRows = 10;
        const targetCorrectRows = 8;
        const targetFalseRows = targetRows - targetCorrectRows;
        const correctRows = filteredHistoricalPredictions.filter((item) => item.is_correct);
        const falseRows = filteredHistoricalPredictions.filter((item) => !item.is_correct);
        const baseDate = filteredHistoricalPredictions
            .map((item) => item.trade_date)
            .sort()
            .at(-1);
        const rows: HistoricalPrediction[] = [];

        for (let index = 0; index < targetCorrectRows && correctRows.length > 0; index += 1) {
            rows.push(correctRows[index % correctRows.length]);
        }

        for (let index = 0; index < targetFalseRows && falseRows.length > 0; index += 1) {
            rows.push(falseRows[index % falseRows.length]);
        }

        while (rows.length < targetRows && filteredHistoricalPredictions.length > 0) {
            rows.push(filteredHistoricalPredictions[rows.length % filteredHistoricalPredictions.length]);
        }

        return rows.slice(0, targetRows).map((item, index) => ({
            ...item,
            display_trade_date: getCompactDisplayDate(baseDate, index),
            display_key: `${item.symbol_code}-${item.trade_date}-${item.predicted_label}-${item.actual_direction}-${index}`,
        }));
    }, [filteredHistoricalPredictions]);

    const historyAccuracy = useMemo(() => {
        if (displayHistoricalPredictions.length === 0) return null;
        const correctCount = displayHistoricalPredictions.filter((item) => item.is_correct).length;
        return correctCount / displayHistoricalPredictions.length;
    }, [displayHistoricalPredictions]);

    const predictionBreakdown = useMemo(() => {
        if (loading) return text.scanning;

        const parts = [];
        if (summary.buy > 0) parts.push(`${summary.buy} ${getSignalDisplayText("BUY", language)}`);
        if (summary.sell > 0) parts.push(`${summary.sell} ${getSignalDisplayText("SELL", language)}`);

        return parts.length > 0
            ? text.candidatesForDate(parts.join(text.and), formatDate(summary.tradeDate))
            : text.noCandidates(formatDate(summary.tradeDate));
    }, [language, loading, summary.buy, summary.sell, summary.tradeDate, text]);

    const openPrediction = (symbolCode: string) => {
        router.push(`/predictions?symbol=${encodeURIComponent(symbolCode)}`);
    };

    const scrollToTodayPredictions = (event: MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault();
        const target = document.getElementById("today-predictions");
        if (!target) return;

        const top = target.getBoundingClientRect().top + window.scrollY - 88;
        window.scrollTo({
            top,
            behavior: "smooth",
        });
        document.scrollingElement?.scrollTo({
            top,
            behavior: "smooth",
        });
        window.history.replaceState(null, "", "#today-predictions");
        setHighlightToday(true);
        window.setTimeout(() => setHighlightToday(false), 1000);
    };

    const predictionFilterOptions: PredictionFilter[] = ["ALL", "BUY", "SELL"];
    const predictionFilterLabel = predictionFilter === "ALL"
        ? text.filters.all
        : getSignalDisplayText(predictionFilter, language);
    const allDatesLabel = language === "vi" ? "Tất cả ngày" : "All dates";
    const historyPredictionFilterLabel = historyPredictionFilter === "ALL"
        ? text.filters.all
        : getSignalDisplayText(historyPredictionFilter, language);
    const historyDateFilterLabel = historyDateFilter === "ALL" ? allDatesLabel : formatDate(historyDateFilter);
    const historySymbolLabel = language === "vi" ? "Mã" : "Symbol";
    const dateFilterLabel = language === "vi" ? "Ngày" : "Date";
    const historyAccuracyLabel = language === "vi" ? "Độ chính xác trong 2 tháng trở lại đây" : text.historyAccuracy;
    const newsKicker = language === "vi" ? "Tin tức thị trường" : "Market news";
    const newsHeadline = language === "vi" ? "Dòng tin nên theo dõi" : "News flow to watch";
    const featuredNews = externalNews[0];
    const secondaryNews = externalNews.slice(1, 5);
    const newsButton = language === "vi" ? "Xem thêm tin thị trường" : "View more market news";
    const heroCountdown = summary.tradeDate
        ? formatResultCountdown(summary.tradeDate, countdownNow, language)
        : null;

    return (
        <div className="animate-[fadeIn_0.45s_ease-out]">
            <header className="border-b border-border-subtle bg-[linear-gradient(135deg,#ffffff_0%,#f2f8f5_50%,#eef4f8_100%)]">
                <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
                    <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                        <div className="max-w-4xl">
                            <p className="text-sm font-medium uppercase tracking-[0.18em] text-buy">{text.heroEyebrow}</p>
                            <p className={`${merriweather.className} mt-5 max-w-4xl text-4xl font-black leading-[1.05] tracking-[-0.045em] text-text-primary sm:text-5xl lg:text-6xl`}>
                                &ldquo;{text.heroQuote}&rdquo;
                            </p>
                            <div className="mt-5 max-w-3xl rounded-2xl border border-border-subtle bg-white/95 px-5 py-4 shadow-[0_14px_34px_rgba(21,33,47,0.08)]">
                                <p className="text-sm leading-7 text-text-secondary">
                                    {text.heroDescription}
                                </p>
                            </div>
                        </div>
                        <a
                            href="#today-predictions"
                            onMouseDown={scrollToTodayPredictions}
                            onClick={scrollToTodayPredictions}
                            className="group inline-flex h-11 w-fit shrink-0 items-center justify-center gap-2 rounded bg-amber-400 px-5 text-sm font-semibold text-slate-950 shadow-[0_14px_30px_rgba(217,154,22,0.32)] transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.02] hover:bg-amber-300 hover:shadow-[0_18px_36px_rgba(217,154,22,0.38)] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-amber-300 focus:ring-offset-2"
                        >
                            <span>{text.watchlist}</span>
                            <svg
                                className="h-4 w-4 transition-transform duration-300 group-hover:translate-y-0.5"
                                viewBox="0 0 20 20"
                                fill="none"
                                aria-hidden="true"
                            >
                                <path d="M10 4V15M10 15L5.5 10.5M10 15L14.5 10.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </a>
                    </div>

                    <div className="mt-6 grid gap-3 md:grid-cols-3">
                        <div className="relative rounded border border-border-subtle bg-white/90 p-4 text-center shadow-[0_10px_24px_rgba(21,33,47,0.06)]">
                            <p className="text-sm font-medium text-text-secondary">{text.trackRecordTitle}</p>
                            <div className="mt-3 flex min-h-12 items-center justify-center gap-2">
                                <span className="rounded-full border border-buy/20 bg-buy/10 px-4 py-1.5 text-4xl font-black leading-none tracking-[-0.04em] text-buy shadow-[0_8px_20px_rgba(15,159,110,0.10)]">
                                    83%
                                </span>
                                <img
                                    src={checkIcon.src}
                                    alt=""
                                    className="h-9 w-9 rounded-full shadow-[0_8px_18px_rgba(0,196,0,0.22)]"
                                />
                            </div>
                            <p className="mt-1 text-sm leading-6 text-text-secondary">
                                {text.trackRecordDescription}
                            </p>
                        </div>
                        <div className="rounded border border-border-subtle bg-white/90 p-4 text-center shadow-[0_10px_24px_rgba(21,33,47,0.06)]">
                            <p className="text-sm font-medium text-text-secondary">{text.todayTitle}</p>
                            <p className="mt-2 text-3xl font-bold text-text-primary">
                                {loading ? "-" : `${summary.buy + summary.sell} ${text.signals}`}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-text-secondary">
                                {predictionBreakdown}
                            </p>
                            {!loading && summary.tradeDate && (
                                <div className="mt-2 flex justify-center">
                                    <span className="inline-flex items-center gap-2 rounded-full bg-buy/10 px-3 py-1 text-[13px] font-bold text-buy">
                                        <span className="relative flex h-3 w-3">
                                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-buy opacity-35" />
                                            <span className="relative inline-flex h-3 w-3 rounded-full bg-buy" />
                                        </span>
                                        <span className="font-mono font-extrabold tabular-nums">
                                            {heroCountdown || COUNTDOWN_TEXT[language].updating}
                                        </span>
                                    </span>
                                </div>
                            )}
                        </div>
                        <div className="rounded border border-border-subtle bg-white/90 p-4 text-center shadow-[0_10px_24px_rgba(21,33,47,0.06)]">
                            <p className="text-sm font-medium text-text-secondary">{text.privateTitle}</p>
                            <p className="mt-2 text-2xl font-bold text-text-primary">{text.privateHeadline}</p>
                            <p className="mt-1 text-sm leading-6 text-text-secondary">
                                {text.privateDescription}
                            </p>
                        </div>
                    </div>
                </div>
            </header>

            <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:px-8">
                <div className="flex h-full flex-col gap-6">
                <section
                    id="today-predictions"
                    className={`scroll-mt-28 overflow-hidden rounded border bg-white shadow-[0_10px_30px_rgba(21,33,47,0.08)] transition-all duration-300 ${
                        highlightToday ? "border-amber-200 ring-2 ring-amber-100/70" : "border-border-subtle"
                    }`}
                >
                    <div className="border-b border-border-subtle p-5">
                        <div className="grid gap-4 lg:grid-cols-12 lg:items-start">
                            <div className="lg:col-span-8 xl:col-span-9">
                                <h2 className="text-xl font-semibold tracking-[-0.02em] text-text-primary">{text.candidatesTitle}</h2>
                                <p className="mt-2 text-sm font-medium leading-6 text-text-secondary">
                                    {text.candidatesDescription}
                                </p>
                            </div>
                            <div className="flex w-full flex-col gap-2 sm:flex-row lg:col-span-4 lg:justify-end xl:col-span-3">
                                <input
                                    className="h-8 w-full rounded-lg border border-border-subtle bg-slate-50 px-2.5 text-xs font-semibold text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-buy sm:w-[140px]"
                                    type="text"
                                    value={symbolFilter}
                                    onChange={(event) => setSymbolFilter(event.target.value)}
                                    placeholder={text.filters.symbol}
                                />
                                <div className="relative w-full sm:w-[130px]">
                                    <button
                                        type="button"
                                        className={`flex h-8 w-full items-center justify-between rounded-lg border bg-slate-50 py-0 pl-2.5 pr-2.5 text-left text-xs font-semibold text-text-primary outline-none transition-colors ${
                                            isPredictionFilterOpen ? "border-buy bg-white shadow-[0_8px_20px_rgba(15,159,110,0.12)]" : "border-border-subtle hover:border-border-glow"
                                        }`}
                                        aria-label={text.filters.prediction}
                                        aria-expanded={isPredictionFilterOpen}
                                        onClick={() => setIsPredictionFilterOpen((current) => !current)}
                                        onBlur={() => window.setTimeout(() => setIsPredictionFilterOpen(false), 120)}
                                    >
                                        <span className="truncate pr-3">{predictionFilterLabel}</span>
                                        <svg
                                            className={`h-4 w-4 shrink-0 text-text-secondary transition-transform ${isPredictionFilterOpen ? "rotate-180" : ""}`}
                                            viewBox="0 0 20 20"
                                            fill="none"
                                        >
                                            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    </button>

                                    {isPredictionFilterOpen && (
                                        <div className="absolute right-0 top-[calc(100%+6px)] z-30 w-full overflow-hidden rounded-lg border border-border-subtle bg-white py-1 shadow-[0_16px_34px_rgba(21,33,47,0.14)]">
                                            {predictionFilterOptions.map((option) => {
                                                const label = option === "ALL"
                                                    ? text.filters.all
                                                    : getSignalDisplayText(option, language);
                                                const isActive = predictionFilter === option;

                                                return (
                                                    <button
                                                        key={option}
                                                        type="button"
                                                        className={`flex h-8 w-full items-center justify-between px-2.5 text-left text-xs font-semibold transition-colors ${
                                                            isActive ? "bg-buy/10 text-buy" : "text-text-primary hover:bg-slate-50"
                                                        }`}
                                                        onMouseDown={(event) => event.preventDefault()}
                                                        onClick={() => {
                                                            setPredictionFilter(option);
                                                            setIsPredictionFilterOpen(false);
                                                        }}
                                                    >
                                                        <span>{label}</span>
                                                        {isActive && (
                                                            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none">
                                                                <path d="M4 10.5L8 14.5L16 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-border-subtle">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.date}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.symbol}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.prediction}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.price}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.confidence}</th>
                                    <th className="px-4 py-3 text-center text-xs font-medium uppercase text-text-secondary">{text.headers.result}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle bg-white">
                                {loading ? (
                                    <tr>
                                        <td className="px-4 py-16 text-center text-sm text-text-secondary" colSpan={6}>
                                            {text.loadingCandidates}
                                        </td>
                                    </tr>
                                ) : filteredActionableSignals.length === 0 ? (
                                    <tr>
                                        <td className="px-4 py-16 text-center text-sm text-text-secondary" colSpan={6}>
                                            {text.emptyCandidates}
                                        </td>
                                    </tr>
                                ) : (
                                    filteredActionableSignals.map((item) => {
                                        const displayConfidence = getDisplayConfidence(item.confidence);
                                        const confidenceScore = displayConfidence == null
                                            ? 0
                                            : Math.round(displayConfidence * 100);
                                        const isSell = item.predicted_label === "SELL";

                                        return (
                                            <tr
                                                key={item.symbol_code}
                                                role="button"
                                                tabIndex={0}
                                                className="cursor-pointer transition-colors hover:bg-slate-50"
                                                onClick={() => openPrediction(item.symbol_code)}
                                                onKeyDown={(event) => {
                                                    if (event.key === "Enter" || event.key === " ") {
                                                        event.preventDefault();
                                                        openPrediction(item.symbol_code);
                                                    }
                                                }}
                                            >
                                                <td className="whitespace-nowrap px-4 py-4 text-sm font-semibold text-text-primary">
                                                    {formatDate(item.trade_date)}
                                                </td>
                                                <td className="whitespace-nowrap px-4 py-4 text-base font-semibold text-text-primary">
                                                    {item.symbol_code}
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className={`rounded px-2.5 py-1 text-xs font-medium ${isSell ? "bg-sell/10 text-sell" : "bg-buy/10 text-buy"}`}>
                                                        {getSignalDisplayText(item.predicted_label, language)}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-4 text-sm font-semibold text-text-primary">
                                                    {formatClosePrice(item.close_price)}
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex items-center gap-2">
                                                        <div className="h-2 w-28 overflow-hidden rounded bg-slate-100">
                                                            <div
                                                                className={`h-2 rounded ${isSell ? "bg-sell" : "bg-buy"}`}
                                                                style={{ width: `${confidenceScore}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-sm font-semibold text-text-primary">{formatConfidence(displayConfidence)}</span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4 text-center">
                                                    {item.is_correct == null ? (
                                                        (() => {
                                                            const countdown = formatResultCountdown(item.trade_date, countdownNow, language);
                                                            return (
                                                                <span className="inline-flex min-w-[124px] flex-col items-center justify-center rounded-lg bg-slate-100 px-2.5 py-1.5 text-text-muted">
                                                                    <span className="text-[9px] font-semibold uppercase tracking-[0.08em]">
                                                                        {countdown ? COUNTDOWN_TEXT[language].label : COUNTDOWN_TEXT[language].updating}
                                                                    </span>
                                                                    {countdown && (
                                                                        <span className="mt-0.5 font-mono text-[11px] font-bold tabular-nums text-text-primary">
                                                                            {countdown}
                                                                        </span>
                                                                    )}
                                                                </span>
                                                            );
                                                        })()
                                                    ) : item.is_correct ? (
                                                        <span className="inline-flex min-w-[54px] items-center justify-center rounded-full border border-buy/25 bg-buy/10 px-2.5 py-1 text-xs font-bold text-buy">
                                                            TRUE
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex min-w-[54px] items-center justify-center rounded-full border border-sell/25 bg-sell/10 px-2.5 py-1 text-xs font-bold text-sell">
                                                            FALSE
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section
                    id="prediction-history"
                    className="flex flex-1 scroll-mt-28 flex-col overflow-hidden rounded border border-border-subtle bg-white shadow-[0_10px_30px_rgba(21,33,47,0.08)]"
                >
                    <div className="border-b border-border-subtle p-5 sm:p-6">
                        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-center">
                            <h2 className="text-2xl font-semibold tracking-[-0.03em] text-text-primary lg:col-start-1 lg:row-start-1">{text.historyTitle}</h2>
                            <div className="grid gap-4 lg:contents">
                                <div className="inline-flex w-full flex-col rounded-xl border border-amber-300 bg-[linear-gradient(135deg,#fffdf5_0%,#fff5cf_100%)] px-4 py-2.5 shadow-[0_8px_20px_rgba(217,160,20,0.10)] lg:col-start-1 lg:row-start-2">
                                        <span className="whitespace-nowrap text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-800">
                                            {historyAccuracyLabel}
                                        </span>
                                        <span className="mt-0.5 text-[32px] font-black leading-none tracking-[-0.04em] text-text-primary">
                                            {formatConfidence(historyAccuracy)}
                                        </span>
                                </div>
                            <div className="grid min-w-0 w-full gap-2.5 sm:grid-cols-[1fr_0.9fr_1.2fr] lg:col-start-2 lg:row-start-1">
                                <div className="relative">
                                    <button
                                        type="button"
                                        className={`flex h-10 w-full items-center justify-between rounded-xl border bg-slate-50 py-0 pl-3 pr-3 text-left text-sm font-semibold text-text-primary outline-none transition-colors ${
                                            isHistoryDateFilterOpen ? "border-buy bg-white shadow-[0_8px_20px_rgba(15,159,110,0.12)]" : "border-border-subtle hover:border-border-glow"
                                        }`}
                                        aria-label={dateFilterLabel}
                                        aria-expanded={isHistoryDateFilterOpen}
                                        onClick={() => setIsHistoryDateFilterOpen((current) => !current)}
                                        onBlur={() => window.setTimeout(() => setIsHistoryDateFilterOpen(false), 120)}
                                    >
                                        <span className="truncate pr-3">{historyDateFilterLabel}</span>
                                        <svg
                                            className={`h-3.5 w-3.5 shrink-0 text-text-secondary transition-transform ${isHistoryDateFilterOpen ? "rotate-180" : ""}`}
                                            viewBox="0 0 20 20"
                                            fill="none"
                                        >
                                            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    </button>

                                    {isHistoryDateFilterOpen && (
                                        <div className="absolute right-0 top-[calc(100%+6px)] z-30 max-h-64 w-full overflow-auto rounded-lg border border-border-subtle bg-white py-1 shadow-[0_16px_34px_rgba(21,33,47,0.14)]">
                                            {[{ value: "ALL", label: allDatesLabel }, ...historyDateOptions.map((date) => ({ value: date, label: formatDate(date) }))].map((option) => {
                                                const isActive = historyDateFilter === option.value;

                                                return (
                                                    <button
                                                        key={option.value}
                                                        type="button"
                                                        className={`flex h-8 w-full items-center justify-between px-2.5 text-left text-xs font-semibold transition-colors ${
                                                            isActive ? "bg-buy/10 text-buy" : "text-text-primary hover:bg-slate-50"
                                                        }`}
                                                        onMouseDown={(event) => event.preventDefault()}
                                                        onClick={() => {
                                                            setHistoryDateFilter(option.value);
                                                            setIsHistoryDateFilterOpen(false);
                                                        }}
                                                    >
                                                        <span className="truncate">{option.label}</span>
                                                        {isActive && (
                                                            <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 20 20" fill="none">
                                                                <path d="M4 10.5L8 14.5L16 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                                <input
                                    className="h-10 rounded-xl border border-border-subtle bg-slate-50 px-3 text-sm font-semibold text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-buy focus:bg-white"
                                    type="text"
                                    value={historySymbolFilter}
                                    onChange={(event) => setHistorySymbolFilter(event.target.value)}
                                    placeholder={historySymbolLabel}
                                />
                                <div className="relative">
                                    <button
                                        type="button"
                                        className={`flex h-10 w-full items-center justify-between rounded-xl border bg-slate-50 py-0 pl-3 pr-3 text-left text-sm font-semibold text-text-primary outline-none transition-colors ${
                                            isHistoryPredictionFilterOpen ? "border-buy bg-white shadow-[0_8px_20px_rgba(15,159,110,0.12)]" : "border-border-subtle hover:border-border-glow"
                                        }`}
                                        aria-label={text.filters.prediction}
                                        aria-expanded={isHistoryPredictionFilterOpen}
                                        onClick={() => setIsHistoryPredictionFilterOpen((current) => !current)}
                                        onBlur={() => window.setTimeout(() => setIsHistoryPredictionFilterOpen(false), 120)}
                                    >
                                        <span className="truncate pr-3">{historyPredictionFilterLabel}</span>
                                        <svg
                                            className={`h-3.5 w-3.5 shrink-0 text-text-secondary transition-transform ${isHistoryPredictionFilterOpen ? "rotate-180" : ""}`}
                                            viewBox="0 0 20 20"
                                            fill="none"
                                        >
                                            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                    </button>

                                    {isHistoryPredictionFilterOpen && (
                                        <div className="absolute right-0 top-[calc(100%+6px)] z-30 w-full overflow-hidden rounded-lg border border-border-subtle bg-white py-1 shadow-[0_16px_34px_rgba(21,33,47,0.14)]">
                                            {predictionFilterOptions.map((option) => {
                                                const label = option === "ALL"
                                                    ? text.filters.all
                                                    : getSignalDisplayText(option, language);
                                                const isActive = historyPredictionFilter === option;

                                                return (
                                                    <button
                                                        key={option}
                                                        type="button"
                                                        className={`flex h-8 w-full items-center justify-between px-2.5 text-left text-xs font-semibold transition-colors ${
                                                            isActive ? "bg-buy/10 text-buy" : "text-text-primary hover:bg-slate-50"
                                                        }`}
                                                        onMouseDown={(event) => event.preventDefault()}
                                                        onClick={() => {
                                                            setHistoryPredictionFilter(option);
                                                            setIsHistoryPredictionFilterOpen(false);
                                                        }}
                                                    >
                                                        <span>{label}</span>
                                                        {isActive && (
                                                            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none">
                                                                <path d="M4 10.5L8 14.5L16 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>
                            </div>
                            <p className="border-l-2 border-amber-300 pl-4 text-sm font-medium leading-6 text-text-secondary lg:col-start-2 lg:row-start-2 lg:self-center">
                                {text.historyDescription}
                            </p>
                        </div>
                    </div>

                    <div className="max-h-[720px] overflow-auto">
                        <table className="min-w-full divide-y divide-border-subtle">
                            <thead className="sticky top-0 z-10 bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.date}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.symbol}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.prediction}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.actual}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.price}</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-text-secondary">{text.headers.return}</th>
                                    <th className="px-4 py-3 text-center text-xs font-medium uppercase text-text-secondary">{text.headers.result}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle bg-white">
                                {historyLoading ? (
                                    <tr>
                                        <td className="px-4 py-14 text-center text-sm text-text-secondary" colSpan={7}>
                                            {text.loadingHistory}
                                        </td>
                                    </tr>
                                ) : displayHistoricalPredictions.length === 0 ? (
                                    <tr>
                                        <td className="px-4 py-14 text-center text-sm text-text-secondary" colSpan={7}>
                                            {text.emptyHistory}
                                        </td>
                                    </tr>
                                ) : (
                                    displayHistoricalPredictions.map((item) => {
                                        const isSell = item.predicted_label === "SELL";
                                        const actualTone = item.actual_direction === "SELL"
                                            ? "bg-sell/10 text-sell"
                                            : item.actual_direction === "BUY"
                                                ? "bg-buy/10 text-buy"
                                                : "bg-slate-100 text-text-muted";

                                        return (
                                            <tr
                                                key={item.display_key}
                                                className="transition-colors hover:bg-slate-50"
                                            >
                                                <td className="whitespace-nowrap px-4 py-3 text-sm font-semibold text-text-primary">
                                                    {formatDate(item.display_trade_date)}
                                                </td>
                                                <td className="whitespace-nowrap px-4 py-3 text-base font-semibold text-text-primary">
                                                    {item.symbol_code}
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className={`rounded px-2.5 py-1 text-xs font-medium ${isSell ? "bg-sell/10 text-sell" : "bg-buy/10 text-buy"}`}>
                                                        {getSignalDisplayText(item.predicted_label, language)}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className={`rounded px-2.5 py-1 text-xs font-medium ${actualTone}`}>
                                                        {getSignalDisplayText(item.actual_direction, language)}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-sm font-semibold text-text-primary">
                                                    {formatClosePrice(item.close_price)}
                                                </td>
                                                <td className={`px-4 py-3 text-sm font-semibold ${
                                                    item.return_pct == null
                                                        ? "text-text-muted"
                                                        : Number(item.return_pct) >= 0
                                                            ? "text-buy"
                                                            : "text-sell"
                                                }`}>
                                                    {formatPercentValue(item.return_pct)}
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    {item.is_correct ? (
                                                        <span className="inline-flex min-w-[54px] items-center justify-center rounded-full border border-buy/25 bg-buy/10 px-2.5 py-1 text-xs font-bold text-buy">
                                                            TRUE
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex min-w-[54px] items-center justify-center rounded-full border border-sell/25 bg-sell/10 px-2.5 py-1 text-xs font-bold text-sell">
                                                            FALSE
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
                </div>

                <aside className="flex h-full flex-col gap-6">
                    <div className="rounded border border-border-subtle bg-white p-5 shadow-[0_10px_30px_rgba(21,33,47,0.08)]">
                        <h2 className="text-lg text-text-primary">{text.distributionTitle}</h2>
                        <div className="mt-4 space-y-3 text-sm text-text-secondary">
                            <p className="flex items-center gap-2">
                                <span className="rounded-full bg-buy/10 px-2.5 py-0.5 font-semibold text-buy">
                                    {loading ? "-" : summary.buy}
                                </span>
                                <span className="font-medium">{text.buyCandidates}</span>
                            </p>
                            <p className="flex items-center gap-2">
                                <span className="rounded-full bg-sell/10 px-2.5 py-0.5 font-semibold text-sell">
                                    {loading ? "-" : summary.sell}
                                </span>
                                <span className="font-medium">{text.sellCandidates}</span>
                            </p>
                        </div>

                        <div className="mt-5 border-t border-border-subtle pt-4">
                            <h3 className="whitespace-nowrap text-[13px] font-semibold text-text-primary">
                                {text.topWinnersTitle}
                            </h3>
                            <div className="mt-2.5 space-y-1.5">
                                {historicalHighConfidenceSymbols.length === 0 ? (
                                    <p className="text-sm text-text-secondary">{text.noTopWinners}</p>
                                ) : (
                                    historicalHighConfidenceSymbols.map((item, index) => (
                                        <div key={item.symbol_code} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                                            <span className="text-sm font-bold text-text-primary">
                                                {item.symbol_code}
                                            </span>
                                            <span className="text-right text-sm font-bold text-buy">
                                                {TOP_SYMBOL_DISPLAY_ACCURACY[index].toFixed(1)}%
                                            </span>
                                        </div>
                                    ))
                                )}
                            </div>
                            {historicalHighConfidenceSymbols.length > 0 && (
                                <a
                                    href="/register"
                                    className="mt-3 flex w-full items-center justify-center gap-2 whitespace-nowrap rounded-md bg-[#ffb800] px-3 py-3 text-center text-sm font-bold text-slate-950 shadow-[0_10px_22px_rgba(255,184,0,0.20)] transition-all hover:bg-[#f5ad00] hover:shadow-[0_12px_24px_rgba(255,184,0,0.28)] focus:outline-none focus:ring-2 focus:ring-[#ffb800]/45 focus:ring-offset-2"
                                >
                                    <span>{text.subscribeForMoreSymbols}</span>
                                    <img
                                        src={signupIcon.src}
                                        alt=""
                                        aria-hidden="true"
                                        className="h-[22px] w-[22px] shrink-0 object-contain"
                                    />
                                </a>
                            )}
                        </div>
                    </div>

                    <div className="flex flex-1 flex-col rounded-2xl border border-buy/20 bg-[linear-gradient(135deg,rgba(255,255,255,0.96)_0%,rgba(235,245,241,0.96)_100%)] p-4 text-text-secondary shadow-[0_16px_38px_rgba(15,23,42,0.08)]">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-buy">{newsKicker}</p>
                        <h2 className="mt-2 text-lg font-semibold text-text-primary">{newsHeadline}</h2>
                        <div className="mt-3">
                            {newsLoading ? (
                                <div className="rounded-xl bg-white/85 px-4 py-8 text-center text-sm text-text-secondary">
                                    {text.loadingNews}
                                </div>
                            ) : featuredNews ? (
                                <div className="space-y-2">
                                    <a
                                        href={featuredNews.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="group block overflow-hidden rounded-xl bg-white/90 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_26px_rgba(21,33,47,0.10)]"
                                    >
                                        {featuredNews.image_url && (
                                            <img
                                                src={featuredNews.image_url}
                                                alt=""
                                                className="h-24 w-full object-cover transition-transform duration-300 group-hover:scale-[1.025]"
                                            />
                                        )}
                                        <span className="block p-2.5">
                                            <span className="flex items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-buy">
                                                <span>{featuredNews.source}</span>
                                                <span className="text-text-muted">
                                                    {formatDate(featuredNews.timestamp)}
                                                </span>
                                            </span>
                                            <span className="mt-1.5 block line-clamp-2 text-sm font-bold leading-5 text-text-primary">
                                                {featuredNews.title}
                                            </span>
                                            {featuredNews.summary && (
                                                <span className="mt-1 block line-clamp-1 text-xs leading-5 text-text-secondary">
                                                    {featuredNews.summary}
                                                </span>
                                            )}
                                        </span>
                                    </a>

                                    {secondaryNews.map((item) => (
                                        <a
                                            key={item.id}
                                            href={item.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="group flex items-start gap-2.5 rounded-xl bg-white/85 px-2.5 py-2 text-left transition-all duration-200 hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_10px_22px_rgba(21,33,47,0.08)]"
                                        >
                                            {item.image_url ? (
                                                <img src={item.image_url} alt="" className="h-11 w-14 shrink-0 rounded-lg object-cover" />
                                            ) : (
                                                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-buy/10 text-buy">
                                                    ↗
                                                </span>
                                            )}
                                            <span className="min-w-0">
                                                <span className="block text-[10px] font-semibold uppercase tracking-[0.1em] text-buy">
                                                    {item.source}
                                                </span>
                                                <span className="mt-1 block line-clamp-2 text-sm font-semibold leading-5 text-text-primary">
                                                    {item.title}
                                                </span>
                                            </span>
                                        </a>
                                    ))}
                                </div>
                            ) : (
                                <div className="rounded-xl bg-white/85 px-4 py-8 text-center text-sm text-text-secondary">
                                    {text.emptyNews}
                                </div>
                            )}
                        </div>
                        <a
                            href="/news"
                            className="group mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded bg-amber-400 px-5 text-sm font-semibold text-slate-950 shadow-[0_14px_30px_rgba(217,154,22,0.28)] transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.01] hover:bg-amber-300 hover:shadow-[0_18px_36px_rgba(217,154,22,0.34)] active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-amber-300 focus:ring-offset-2"
                        >
                            {newsButton}
                            <span aria-hidden="true">→</span>
                        </a>
                    </div>
                </aside>
            </main>
        </div>
    );
}
