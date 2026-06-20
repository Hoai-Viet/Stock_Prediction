"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useLanguage } from "@/components/LanguageProvider";

export default function DataExplorer() {
    const { language } = useLanguage();
    const text = language === "vi"
        ? {
            title: "Khám phá dữ liệu",
            raw: "CHỈ SỐ GỐC",
            features: "CHỈ SỐ KỸ THUẬT",
            date: "Ngày",
            symbol: "Mã",
            metric: "Mã chỉ số",
            value: "Giá trị",
            loading: "Đang tải dữ liệu...",
        }
        : {
            title: "Data Explorer",
            raw: "RAW METRICS",
            features: "TECHNICAL METRICS",
            date: "Date",
            symbol: "Symbol",
            metric: "Metric Code",
            value: "Value",
            loading: "Loading data...",
        };
    const [data, setData] = useState<any[]>([]);
    const [mode, setMode] = useState("feature");

    useEffect(() => {
        setTimeout(() => {
            if (mode === "raw") {
                setData([
                    { period_date: "2026-04-07", symbol_code: "FPT", metric_code: "close_price", metric_value: "115.5" },
                    { period_date: "2026-04-07", symbol_code: "VIC", metric_code: "volume", metric_value: "1500000" },
                    { period_date: "2026-04-06", symbol_code: "FPT", metric_code: "close_price", metric_value: "114.2" },
                    { period_date: "2026-04-06", symbol_code: "VIC", metric_code: "volume", metric_value: "1200000" }
                ]);
            } else {
                setData([
                    { period_date: "2026-04-07", symbol_code: "FPT", metric_code: "feat_rsi_14", metric_value: "65.2" },
                    { period_date: "2026-04-07", symbol_code: "VIC", metric_code: "feat_macd", metric_value: "-1.5" },
                    { period_date: "2026-04-06", symbol_code: "FPT", metric_code: "feat_rsi_14", metric_value: "62.1" },
                    { period_date: "2026-04-06", symbol_code: "VIC", metric_code: "feat_macd", metric_value: "-1.2" }
                ]);
            }
        }, 500);
    }, [mode]);

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-[24px] font-semibold text-text-primary">{text.title}</h1>
                <div className="flex gap-2">
                    <button
                        onClick={() => setMode("raw")}
                        className={`inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] cursor-pointer outline-none ${mode === 'raw' ? 'bg-buy/10 text-buy border border-buy/25' : 'bg-slate-100 text-silent border border-border-subtle'}`}
                    >
                        {text.raw}
                    </button>
                    <button
                        onClick={() => setMode("feature")}
                        className={`inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] cursor-pointer outline-none ${mode === 'feature' ? 'bg-buy/10 text-buy border border-buy/25' : 'bg-slate-100 text-silent border border-border-subtle'}`}
                    >
                        {text.features}
                    </button>
                </div>
            </div>

            <div className="bg-bg-card border border-border-subtle rounded-[14px] p-0 backdrop-blur-[8px] overflow-x-auto">
                <table className="w-full border-collapse text-[13px]">
                    <thead>
                        <tr>
                            <th className="text-left py-2.5 px-3.5 text-text-muted font-semibold text-[11px] uppercase tracking-[0.6px] border-b border-border-subtle">{text.date}</th>
                            <th className="text-left py-2.5 px-3.5 text-text-muted font-semibold text-[11px] uppercase tracking-[0.6px] border-b border-border-subtle">{text.symbol}</th>
                            <th className="text-left py-2.5 px-3.5 text-text-muted font-semibold text-[11px] uppercase tracking-[0.6px] border-b border-border-subtle">{text.metric}</th>
                            <th className="text-right py-2.5 px-3.5 text-text-muted font-semibold text-[11px] uppercase tracking-[0.6px] border-b border-border-subtle">{text.value}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, i) => (
                            <tr key={i} className="hover:bg-slate-50 transition-colors duration-150">
                                <td className="py-3 px-3.5 border-b border-border-subtle text-text-primary">{new Date(row.period_date).toLocaleDateString()}</td>
                                <td className="py-3 px-3.5 border-b border-border-subtle text-text-primary font-bold">{row.symbol_code}</td>
                                <td className="py-3 px-3.5 border-b border-white/5 bg-accent-gradient bg-clip-text text-transparent w-max inline-block">{row.metric_code}</td>
                                <td className="py-3 px-3.5 border-b border-border-subtle text-text-primary text-right">{parseFloat(row.metric_value).toFixed(4)}</td>
                            </tr>
                        ))}
                        {data.length === 0 && (
                            <tr><td colSpan={4} className="text-center p-5 text-text-muted">{text.loading}</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
