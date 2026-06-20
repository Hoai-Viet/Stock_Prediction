"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { useLanguage } from "@/components/LanguageProvider";

export default function Signals() {
    const { language } = useLanguage();
    const text = language === "vi"
        ? {
            title: "Tín hiệu có thể hành động hôm nay",
            waiting: "Đang chờ tín hiệu thị trường mới nhất...",
            entryPrice: "GIÁ VÀO LỆNH",
            model: "MÔ HÌNH",
        }
        : {
            title: "Actionable Signals (Today)",
            waiting: "Waiting for latest market signals...",
            entryPrice: "ENTRY PRICE",
            model: "MODEL",
        };
    const [signals, setSignals] = useState<any[]>([]);

    useEffect(() => {
        setTimeout(() => {
            setSignals([
                { symbol_code: "FPT", predicted_label: "BUY", entry_price: "115.5", model_version: "v1.2.0" },
                { symbol_code: "VIC", predicted_label: "SELL", entry_price: "45.2", model_version: "v1.2.0" },
                { symbol_code: "VCB", predicted_label: "BUY", entry_price: "92.0", model_version: "v1.2.0" }
            ]);
        }, 500);
    }, []);

    return (
        <div>
            <div className="flex items-center justify-between mb-4">
                <h1 className="text-[24px] font-semibold text-text-primary">{text.title}</h1>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4 mb-6">
                {signals.length === 0 && <p className="px-4 text-text-muted">{text.waiting}</p>}
                {signals.map((sig, i) => (
                    <div key={i} className="bg-bg-card border border-border-subtle rounded-[14px] p-5 backdrop-blur-[8px] transition-all duration-200 hover:border-border-glow hover:shadow-[0_10px_30px_rgba(21,33,47,0.08)] relative overflow-hidden">
                        <div className={`absolute top-0 left-0 h-[3px] w-full ${sig.predicted_label === 'BUY' ? 'bg-buy' : 'bg-sell'}`}></div>
                        <div className="flex justify-between items-center mb-3">
                            <span className="text-[22px] font-bold">{sig.symbol_code}</span>
                            <span className={`inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] ${sig.predicted_label === 'BUY' ? 'bg-buy/10 text-buy border border-buy/25' :
                                'bg-sell/10 text-sell border border-sell/25'
                                }`}>
                                {sig.predicted_label}
                            </span>
                        </div>

                        <div className="flex justify-between mt-4">
                            <div>
                                <div className="text-[11px] font-medium text-text-muted uppercase tracking-[0.8px]">{text.entryPrice}</div>
                                <div className="font-semibold mt-1 text-[15px]">
                                    {sig.entry_price ? `$${parseFloat(sig.entry_price).toFixed(2)}` : 'N/A'}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-[11px] font-medium text-text-muted uppercase tracking-[0.8px]">{text.model}</div>
                                <div className="text-text-muted font-semibold mt-1 text-[13px]">{sig.model_version}</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
