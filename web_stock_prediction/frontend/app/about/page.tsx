"use client";

import Link from "next/link";
import { useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

const DetailIcon = ({ variant }: { variant: "area" | "task" }) => {
    if (variant === "area") {
        return (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        );
    }

    return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M9 11l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
        </svg>
    );
};

const PIPELINE_STEPS_EN = [
    {
        title: "Data collection",
        description: "Daily market data and calculated technical metrics are refreshed into the warehouse before any signal is published.",
        tasks: [
            "Load market snapshots and reference symbol data into the warehouse.",
            "Refresh technical metrics that are later used for screening and validation.",
            "Keep historical coverage aligned so both new and backfilled dates can be reviewed.",
        ],
    },
    {
        title: "Feature screening",
        description: "Market behavior is evaluated and tracked first, then translated into BUY and SELL-ready views for downstream prediction.",
        tasks: [
            "Assess price action, volume flow, momentum, and volatility to form an initial market view for each symbol.",
            "Combine machine learning signals with association rule mining to discover rule sets linked to the highest win rates.",
            "Apply the strongest validated rule combinations to the current dataset to filter practical BUY and SELL candidates.",
        ],
    },
    {
        title: "Signal decision",
        description: "Qualified rule combinations are matched against the latest metrics to label symbols as BUY, SELL, or HOLD.",
        tasks: [
            "Match the latest symbol metrics against trusted rule combinations.",
            "Assign BUY or SELL only when the latest setup satisfies the required combination logic.",
            "Leave the symbol as HOLD when no qualified setup is present.",
        ],
    },
    {
        title: "Validation loop",
        description: "Historical predictions are compared with realized next-session direction to track accuracy over time.",
        tasks: [
            "Compare predicted direction with the realized next-session move.",
            "Mark past records as correct or incorrect for later review.",
            "Surface accuracy trends in the dashboard so weak areas can be inspected quickly.",
        ],
    },
];

const PIPELINE_STEPS_VI = [
    {
        title: "Thu thập dữ liệu",
        description: "Dữ liệu thị trường hằng ngày và các chỉ số kỹ thuật được cập nhật vào kho dữ liệu trước khi tín hiệu được công bố.",
        tasks: [
            "Nạp dữ liệu thị trường và thông tin tham chiếu của từng mã vào kho dữ liệu.",
            "Cập nhật các chỉ số kỹ thuật phục vụ sàng lọc và kiểm chứng tín hiệu.",
            "Đồng bộ dữ liệu lịch sử để có thể đánh giá cả ngày mới lẫn các giai đoạn cần bổ sung.",
        ],
    },
    {
        title: "Sàng lọc đặc trưng",
        description: "Diễn biến thị trường được đánh giá và theo dõi trước, sau đó chuyển thành góc nhìn sẵn sàng cho dự báo BUY và SELL.",
        tasks: [
            "Đánh giá hành động giá, dòng tiền, động lượng và biến động để hình thành nhận định ban đầu cho từng mã.",
            "Kết hợp tín hiệu học máy với khai phá luật kết hợp để tìm các tập luật có tỷ lệ thắng cao nhất.",
            "Áp dụng các tổ hợp luật đã được kiểm chứng lên dữ liệu hiện tại để lọc ứng viên MUA và BÁN thực tế.",
        ],
    },
    {
        title: "Ra quyết định tín hiệu",
        description: "Các tổ hợp luật đạt chuẩn được đối chiếu với dữ liệu mới nhất để gán nhãn BUY, SELL hoặc HOLD.",
        tasks: [
            "Đối chiếu chỉ số mới nhất của từng mã với các tổ hợp luật đáng tin cậy.",
            "Chỉ gán BUY hoặc SELL khi dữ liệu hiện tại thỏa đầy đủ logic yêu cầu.",
            "Giữ nhãn HOLD khi chưa xuất hiện một thiết lập đủ tiêu chuẩn.",
        ],
    },
    {
        title: "Vòng lặp kiểm chứng",
        description: "Dự báo lịch sử được so sánh với hướng giá của phiên kế tiếp để theo dõi độ chính xác theo thời gian.",
        tasks: [
            "So sánh hướng dự báo với biến động thực tế của phiên kế tiếp.",
            "Đánh dấu dự báo đúng hoặc sai để phục vụ đánh giá sau này.",
            "Hiển thị xu hướng độ chính xác trên dashboard để nhận ra điểm yếu nhanh chóng.",
        ],
    },
];

const DASHBOARD_AREAS_EN = [
    {
        title: "Overview",
        description: "Quick daily shortlist with confidence scores and direct navigation to symbol detail.",
        details: [
            "Highlights the latest shortlist for the session.",
            "Shows symbol, prediction, close price, and confidence at a glance.",
            "Lets users jump straight into the detailed prediction page for a selected symbol.",
        ],
    },
    {
        title: "Predictions",
        description: "Per-symbol chart view, latest signal, validation history, and related market context.",
        details: [
            "Shows chart context and recent market movement for the selected symbol.",
            "Displays the current prediction and the historical validation record.",
            "Keeps the detail page focused on review rather than raw warehouse tables.",
        ],
    },
    {
        title: "Operations",
        description: "Scheduled jobs update metrics, backfill historical outcomes, and keep the decision table current.",
        details: [
            "Refreshes computed metrics on a schedule.",
            "Updates historical prediction outcomes after later prices become available.",
            "Keeps the dashboard synchronized with warehouse-side decision data.",
        ],
    },
];

const DASHBOARD_AREAS_VI = [
    {
        title: "Tổng quan",
        description: "Danh sách rút gọn hằng ngày với độ tin cậy và liên kết trực tiếp đến từng mã.",
        details: [
            "Nêu bật các mã đáng chú ý nhất trong phiên.",
            "Hiển thị mã, dự báo, giá đóng cửa và độ tin cậy trong một góc nhìn.",
            "Cho phép mở ngay trang dự báo chi tiết của mã được chọn.",
        ],
    },
    {
        title: "Dự báo",
        description: "Biểu đồ từng mã, tín hiệu mới nhất, lịch sử kiểm chứng và bối cảnh thị trường liên quan.",
        details: [
            "Hiển thị biểu đồ và diễn biến thị trường gần đây của mã được chọn.",
            "Trình bày dự báo hiện tại cùng lịch sử kiểm chứng.",
            "Tập trung vào thông tin cần đánh giá thay vì các bảng dữ liệu thô.",
        ],
    },
    {
        title: "Vận hành",
        description: "Các tác vụ định kỳ cập nhật chỉ số, bổ sung kết quả lịch sử và duy trì bảng quyết định mới nhất.",
        details: [
            "Cập nhật các chỉ số đã tính toán theo lịch.",
            "Bổ sung kết quả thực tế của dự báo lịch sử khi có giá phiên sau.",
            "Giữ dashboard đồng bộ với dữ liệu quyết định trong kho dữ liệu.",
        ],
    },
];

const ABOUT_TEXT = {
    en: {
        overview: "Project overview",
        title: "Stock prediction workflow from market data to decision dashboard",
        description: "This project turns daily trading data into practical BUY, SELL, and HOLD signals, then exposes those signals through a warehouse-backed prediction dashboard.",
        openPredictions: "Open predictions",
        detail: "Detail",
        howItWorks: "How the project works",
        pipelineDescription: "The pipeline is designed to keep signal generation consistent and measurable.",
        flow: "End-to-end flow",
        task: "Task",
        coreInputs: "Core inputs",
        coreInputLines: [
            "Price action: open, high, low, close, and multi-day return behavior.",
            "Volume behavior: raw volume, moving averages, and accumulation or distribution context.",
            "Technical context: momentum, volatility bands, and breakout-style conditions.",
        ],
        uiTitle: "What the UI shows",
        uiLines: [
            "Today's candidates with confidence and direct row navigation.",
            "Symbol-level chart review with current signal and validation history.",
            "Historical comparison between predicted direction and realized move.",
        ],
        objective: "Objective",
        objectiveDescription: "The goal is not to automate trading blindly. The system narrows the watchlist, scores signal quality, and gives a structured base for manual review.",
    },
    vi: {
        overview: "Tổng quan dự án",
        title: "Quy trình dự báo cổ phiếu từ dữ liệu thị trường đến bảng quyết định",
        description: "Dự án chuyển dữ liệu giao dịch hằng ngày thành tín hiệu BUY, SELL và HOLD thực tế, sau đó trình bày chúng trên dashboard dự báo được đồng bộ từ kho dữ liệu.",
        openPredictions: "Mở trang dự báo",
        detail: "Chi tiết",
        howItWorks: "Dự án vận hành như thế nào",
        pipelineDescription: "Quy trình được thiết kế để việc tạo tín hiệu luôn nhất quán và có thể đo lường.",
        flow: "Quy trình toàn diện",
        task: "Công việc",
        coreInputs: "Dữ liệu đầu vào chính",
        coreInputLines: [
            "Hành động giá: giá mở cửa, cao nhất, thấp nhất, đóng cửa và mức sinh lời nhiều ngày.",
            "Dòng tiền: khối lượng, đường trung bình và bối cảnh tích lũy hoặc phân phối.",
            "Bối cảnh kỹ thuật: động lượng, dải biến động và các điều kiện bứt phá.",
        ],
        uiTitle: "Giao diện hiển thị gì",
        uiLines: [
            "Danh sách ứng viên hôm nay cùng độ tin cậy và liên kết trực tiếp.",
            "Biểu đồ từng mã với tín hiệu hiện tại và lịch sử kiểm chứng.",
            "So sánh lịch sử giữa hướng dự báo và biến động thực tế.",
        ],
        objective: "Mục tiêu",
        objectiveDescription: "Mục tiêu không phải tự động giao dịch một cách mù quáng. Hệ thống thu gọn danh sách theo dõi, đánh giá chất lượng tín hiệu và cung cấp nền tảng có cấu trúc để nhà đầu tư tự xem xét.",
    },
};

export default function AboutPage() {
    const { language } = useLanguage();
    const text = ABOUT_TEXT[language];
    const pipelineSteps = language === "vi" ? PIPELINE_STEPS_VI : PIPELINE_STEPS_EN;
    const dashboardAreas = language === "vi" ? DASHBOARD_AREAS_VI : DASHBOARD_AREAS_EN;
    const [openSteps, setOpenSteps] = useState<number[]>([0]);
    const [openAreas, setOpenAreas] = useState<number[]>([0]);

    const toggleOpenState = (index: number, current: number[], setter: (value: number[]) => void) => {
        if (current.includes(index)) {
            setter(current.filter((item) => item !== index));
            return;
        }

        setter([...current, index]);
    };

    return (
        <div className="mx-auto max-w-7xl animate-[fadeIn_0.45s_ease-out] px-4 py-6 sm:px-6 lg:px-8">
            <section className="overflow-hidden rounded-[18px] border border-border-subtle bg-white shadow-[0_10px_30px_rgba(21,33,47,0.08)]">
                <div className="bg-[linear-gradient(135deg,#f8fbff_0%,#eef4f8_45%,#f7fafc_100%)] px-6 py-8 sm:px-8">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                        <div className="max-w-3xl">
                            <p className="text-sm text-text-secondary">{text.overview}</p>
                            <h1 className="mt-1 text-3xl font-semibold tracking-[-0.03em] text-text-primary sm:text-4xl">
                                {text.title}
                            </h1>
                            <p className="mt-3 max-w-2xl text-sm leading-7 text-text-secondary">
                                {text.description}
                            </p>
                        </div>

                        <Link
                            href="/predictions"
                            className="inline-flex h-10 w-fit items-center justify-center rounded bg-accent-purple px-4 text-sm font-medium text-white transition-colors hover:bg-accent-blue"
                        >
                            {text.openPredictions}
                        </Link>
                    </div>
                </div>
            </section>

            <section className="mt-6 grid gap-4 md:grid-cols-3">
                {dashboardAreas.map((item, index) => (
                    <button
                        key={item.title}
                        type="button"
                        onClick={() => toggleOpenState(index, openAreas, setOpenAreas)}
                        className={`rounded-[16px] border bg-white p-5 text-left shadow-[0_10px_30px_rgba(21,33,47,0.08)] transition-all duration-200 ${
                            openAreas.includes(index) ? "border-border-glow" : "border-border-subtle"
                        }`}
                    >
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <div className="text-lg font-semibold text-text-primary">{item.title}</div>
                                <p className="mt-2 text-sm leading-6 text-text-secondary">{item.description}</p>
                            </div>
                            <span
                                className={`mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-50 text-text-secondary transition-transform duration-200 ${
                                    openAreas.includes(index) ? "rotate-180" : ""
                                }`}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                    <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </span>
                        </div>

                        <div
                            className={`grid transition-all duration-300 ${
                                openAreas.includes(index) ? "mt-4 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                            }`}
                        >
                            <div className="overflow-hidden">
                                <div className="ml-2 border-l border-border-subtle pl-4 pt-4">
                                    <div className="space-y-3 text-sm text-text-secondary">
                                        {item.details.map((detail, detailIndex) => (
                                            <div
                                                key={detail}
                                                className="flex gap-3 rounded-[12px] border border-border-subtle bg-slate-50 px-3 py-3"
                                            >
                                                <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-accent-purple shadow-sm">
                                                    <DetailIcon variant="area" />
                                                </span>
                                                <div className="min-w-0">
                                                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                                                        {text.detail} {detailIndex + 1}
                                                    </div>
                                                    <p className="mt-1 leading-6 text-text-secondary">{detail}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </button>
                ))}
            </section>

            <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <div className="rounded-[16px] border border-border-subtle bg-white p-6 shadow-[0_10px_30px_rgba(21,33,47,0.08)]">
                    <div className="flex items-center justify-between border-b border-border-subtle pb-4">
                        <div>
                            <h2 className="text-xl font-semibold text-text-primary">{text.howItWorks}</h2>
                            <p className="mt-1 text-sm text-text-secondary">
                                {text.pipelineDescription}
                            </p>
                        </div>
                        <span className="rounded-full bg-buy/10 px-3 py-1 text-xs font-medium text-buy">
                            {text.flow}
                        </span>
                    </div>

                    <div className="mt-6 space-y-4">
                        {pipelineSteps.map((step, index) => (
                            <button
                                key={step.title}
                                type="button"
                                onClick={() => toggleOpenState(index, openSteps, setOpenSteps)}
                                className={`w-full rounded-[14px] border px-4 py-4 text-left transition-all duration-200 ${
                                    openSteps.includes(index) ? "border-border-glow bg-white" : "border-border-subtle bg-slate-50"
                                }`}
                            >
                                <div className="flex gap-4">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-purple text-sm font-semibold text-white">
                                        {index + 1}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <div className="text-base font-semibold text-text-primary">{step.title}</div>
                                                <p className="mt-1 text-sm leading-6 text-text-secondary">{step.description}</p>
                                            </div>
                                            <span
                                                className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-50 text-text-secondary transition-transform duration-200 ${
                                                    openSteps.includes(index) ? "rotate-180" : ""
                                                }`}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                                                    <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                </svg>
                                            </span>
                                        </div>

                                        <div
                                            className={`grid transition-all duration-300 ${
                                                openSteps.includes(index) ? "mt-4 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                                            }`}
                                        >
                                            <div className="overflow-hidden">
                                                <div className="ml-2 border-l border-border-subtle pl-4 pt-4">
                                                    <div className="space-y-3 text-sm text-text-secondary">
                                                        {step.tasks.map((task, taskIndex) => (
                                                            <div
                                                                key={task}
                                                                className="flex gap-3 rounded-[12px] border border-border-subtle bg-slate-50 px-3 py-3"
                                                            >
                                                                <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-buy shadow-sm">
                                                                    <DetailIcon variant="task" />
                                                                </span>
                                                                <div className="min-w-0">
                                                                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                                                                        {text.task} {taskIndex + 1}
                                                                    </div>
                                                                    <p className="mt-1 leading-6 text-text-secondary">{task}</p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="rounded-[16px] border border-border-subtle bg-white p-6 shadow-[0_10px_30px_rgba(21,33,47,0.08)]">
                        <h2 className="text-lg font-semibold text-text-primary">{text.coreInputs}</h2>
                        <div className="mt-4 space-y-3 text-sm text-text-secondary">
                            {text.coreInputLines.map((line) => <p key={line}>{line}</p>)}
                        </div>
                    </div>

                    <div className="rounded-[16px] border border-border-subtle bg-white p-6 shadow-[0_10px_30px_rgba(21,33,47,0.08)]">
                        <h2 className="text-lg font-semibold text-text-primary">{text.uiTitle}</h2>
                        <div className="mt-4 space-y-3 text-sm text-text-secondary">
                            {text.uiLines.map((line) => <p key={line}>{line}</p>)}
                        </div>
                    </div>

                    <div className="rounded-[16px] border border-border-subtle bg-[linear-gradient(135deg,#f8fbff_0%,#eef6f3_100%)] p-6">
                        <h2 className="text-lg font-semibold text-text-primary">{text.objective}</h2>
                        <p className="mt-3 text-sm leading-6 text-text-secondary">
                            {text.objectiveDescription}
                        </p>
                    </div>
                </div>
            </section>
        </div>
    );
}
