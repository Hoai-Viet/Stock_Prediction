"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

const FOOTER_TEXT = {
    en: {
        tagline: "Clearer signals for more disciplined investment decisions.",
        explore: "Explore",
        overview: "Overview",
        predictions: "Predictions",
        marketNews: "Market news",
        about: "About the project",
        support: "Investor access",
        register: "Register for signals",
        contact: "Contact support",
        disclaimer:
            "Market forecasts are provided for informational purposes and do not constitute investment advice.",
        copyright: "Stock Predictor. All rights reserved.",
    },
    vi: {
        tagline: "Tín hiệu rõ ràng hơn cho những quyết định đầu tư kỷ luật hơn.",
        explore: "Khám phá",
        overview: "Tổng quan",
        predictions: "Dự báo",
        marketNews: "Tin tức thị trường",
        about: "Về dự án",
        support: "Dành cho nhà đầu tư",
        register: "Đăng ký nhận tín hiệu",
        contact: "Liên hệ hỗ trợ",
        disclaimer:
            "Các dự báo thị trường chỉ mang tính chất tham khảo và không phải là khuyến nghị đầu tư.",
        copyright: "Stock Predictor. Bảo lưu mọi quyền.",
    },
};

export default function Footer() {
    const { language } = useLanguage();
    const text = FOOTER_TEXT[language];

    return (
        <footer className="border-t border-white/15 bg-accent-gradient text-slate-200">
            <div className="mx-auto grid max-w-7xl items-center gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[1.15fr_1.25fr_auto] lg:px-8">
                <div className="max-w-md">
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-sm font-semibold tracking-[0.16em] text-white transition-opacity hover:opacity-80"
                    >
                        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="#10a36f" />
                        </svg>
                        STOCK PREDICTOR
                    </Link>
                    <p className="mt-1.5 text-xs leading-5 text-slate-300">{text.tagline}</p>
                </div>

                <div>
                    <h2 className="sr-only">{text.explore}</h2>
                    <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium">
                        <Link className="w-fit transition-colors hover:text-emerald-300" href="/">
                            {text.overview}
                        </Link>
                        <Link className="w-fit transition-colors hover:text-emerald-300" href="/predictions">
                            {text.predictions}
                        </Link>
                        <Link className="w-fit transition-colors hover:text-emerald-300" href="/news">
                            {text.marketNews}
                        </Link>
                        <Link className="w-fit transition-colors hover:text-emerald-300" href="/about">
                            {text.about}
                        </Link>
                    </nav>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <h2 className="sr-only">{text.support}</h2>
                    <div className="flex flex-wrap items-center gap-3 text-xs">
                        <Link
                            href="/predictions"
                            className="inline-flex w-fit items-center gap-2 rounded-lg bg-buy px-3.5 py-2 font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-buy-hover"
                        >
                            {text.register}
                            <span aria-hidden="true">-&gt;</span>
                        </Link>
                        <a className="w-fit transition-colors hover:text-emerald-300" href="mailto:support@stockpredictor.vn">
                            {text.contact}
                        </a>
                    </div>
                </div>
            </div>

            <div className="border-t border-white/15">
                <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-2.5 text-[11px] leading-4 text-slate-300 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
                    <p>{text.disclaimer}</p>
                    <p className="shrink-0">&copy; 2026 {text.copyright}</p>
                </div>
            </div>
        </footer>
    );
}
