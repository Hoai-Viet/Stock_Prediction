"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useLanguage } from "@/components/LanguageProvider";

export default function ModelMetrics() {
    const { language } = useLanguage();
    const text = language === "vi"
        ? {
            title: "Chỉ số mô hình",
            empty: "Chưa có chỉ số. Hãy chờ kết quả thực tế được cập nhật.",
            class: "Nhóm",
            precision: "ĐỘ CHÍNH XÁC",
            total: "TỔNG DỰ BÁO",
        }
        : {
            title: "Model Metrics",
            empty: "No metrics found. Wait for outcomes to resolve.",
            class: "Class",
            precision: "PRECISION",
            total: "TOTAL PREDICTIONS",
        };
    const [metrics, setMetrics] = useState<any[]>([]);

    useEffect(() => {
        setTimeout(() => {
            setMetrics([
                { label: "BUY", model_version: "v1.2.0", precision_pct: 75.2, total: 450 },
                { label: "SELL", model_version: "v1.2.0", precision_pct: 68.9, total: 320 },
                { label: "HOLD", model_version: "v1.2.0", precision_pct: 82.1, total: 1200 }
            ]);
        }, 500);
    }, []);

    return (
        <div>
            <h1 className="text-[24px] font-semibold text-text-primary mb-6">{text.title}</h1>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4 mb-6">
                {metrics.length === 0 && <p className="text-text-muted px-4">{text.empty}</p>}
                {metrics.map((m, i) => (
                    <div key={i} className="bg-bg-card border border-border-subtle rounded-[14px] p-5 backdrop-blur-[8px] transition-all duration-200 hover:border-border-glow hover:shadow-[0_10px_30px_rgba(21,33,47,0.08)] flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                            <h3 className="text-[18px] font-bold">
                                {text.class} <span className={`text-${m.label.toLowerCase()}`}>{m.label}</span>
                            </h3>
                            <span className="inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] bg-gray-500/15 text-silent border border-gray-500/30">{m.model_version}</span>
                        </div>

                        <div className="mt-4 flex justify-between">
                            <div>
                                <div className="text-[11px] font-medium text-text-muted uppercase tracking-[0.8px]">{text.precision}</div>
                                <div className="text-[24px] font-extrabold mt-1.5 leading-none bg-accent-gradient bg-clip-text text-transparent">{m.precision_pct}%</div>
                            </div>
                            <div className="text-right">
                                <div className="text-[11px] font-medium text-text-muted uppercase tracking-[0.8px]">{text.total}</div>
                                <div className="text-[24px] font-extrabold mt-1.5 leading-none">{m.total}</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
