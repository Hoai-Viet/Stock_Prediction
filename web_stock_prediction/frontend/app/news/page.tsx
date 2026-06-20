"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

interface NewsItem {
    id: string;
    title: string;
    category: string;
    sentiment: string;
    source: string;
    timestamp: string;
    summary: string;
    url: string;
    image_url?: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function NewsPage() {
    const { language } = useLanguage();
    const text = language === "vi"
        ? {
            title: "Tin tức thị trường",
            description: "Cập nhật mới nhất và phân tích tâm lý trên thị trường tài chính Việt Nam.",
            loading: "Đang tải luồng tin tức mới nhất...",
            empty: "Chưa tải được tin tức từ các nguồn bên ngoài.",
            readMore: "Đọc bài gốc",
            positive: "Tích cực",
            negative: "Tiêu cực",
            neutral: "Trung tính",
        }
        : {
            title: "Market News",
            description: "Latest updates and sentiment analysis across the Vietnamese financial markets.",
            loading: "Fetching latest news streams...",
            empty: "External market news is not available yet.",
            readMore: "Read original",
            positive: "Positive",
            negative: "Negative",
            neutral: "Neutral",
        };
    const [news, setNews] = useState<NewsItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let ignore = false;

        async function loadNews() {
            setLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/api/news/external?limit=18`);
                if (!response.ok) {
                    throw new Error("Failed to load external news");
                }
                const payload = (await response.json()) as { news?: NewsItem[] };
                if (!ignore) {
                    setNews(payload.news || []);
                }
            } catch {
                if (!ignore) {
                    setNews([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        }

        loadNews();

        return () => {
            ignore = true;
        };
    }, []);

    const getSentimentBadge = (sentiment: string) => {
        if (sentiment === "Positive") return <span className="inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] bg-buy/10 text-buy border border-buy/25">{text.positive}</span>;
        if (sentiment === "Negative") return <span className="inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] bg-sell/10 text-sell border border-sell/25">{text.negative}</span>;
        return <span className="inline-flex items-center px-2.5 py-[3px] rounded-full text-[11px] font-bold tracking-[0.5px] bg-slate-100 text-silent border border-border-subtle">{text.neutral}</span>;
    };

    return (
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
            <header className="flex items-center justify-between mb-4">
                <div>
                    <h1 className="text-[28px] font-extrabold mb-2 bg-accent-gradient bg-clip-text text-transparent">{text.title}</h1>
                    <p className="text-[14px] text-text-secondary">{text.description}</p>
                </div>
            </header>

            {loading ? (
                <div className="p-[60px] text-center text-text-muted">
                    <div className="inline-block w-9 h-9 border-[3px] border-border-subtle border-t-accent-purple rounded-full animate-spin" />
                    <p className="mt-4 text-[14px] tracking-[0.5px]">{text.loading}</p>
                </div>
            ) : news.length === 0 ? (
                <div className="rounded-[14px] border border-border-subtle bg-white p-12 text-center text-text-secondary">
                    {text.empty}
                </div>
            ) : (
                <div className="grid grid-cols-[repeat(auto-fill,minmax(360px,1fr))] gap-6">
                    {news.map(item => (
                        <a
                            key={item.id}
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="bg-bg-card border border-border-subtle rounded-[14px] backdrop-blur-[8px] transition-all duration-200 hover:-translate-y-0.5 hover:border-border-glow hover:shadow-[0_10px_30px_rgba(21,33,47,0.08)] relative flex flex-col overflow-hidden"
                        >
                            <div className={`absolute top-0 left-0 w-1 h-full ${item.sentiment === 'Positive' ? 'bg-buy' : item.sentiment === 'Negative' ? 'bg-sell' : 'bg-slate-400'}`}></div>

                            {item.image_url && (
                                <img src={item.image_url} alt="" className="h-48 w-full object-cover" />
                            )}

                            <div className="flex flex-1 flex-col p-6">
                            <div className="flex justify-between items-start mb-4 pl-2">
                                <span className="text-[11px] font-semibold text-accent-purple uppercase tracking-[0.8px]">
                                    {item.category}
                                </span>
                                {getSentimentBadge(item.sentiment)}
                            </div>

                            <h3 className="text-[17px] font-bold text-text-primary mb-3 leading-snug pl-2">
                                {item.title}
                            </h3>

                            <p className="text-[14px] text-text-secondary leading-relaxed flex-1 mb-5 pl-2">
                                {item.summary}
                            </p>

                            <div className="flex justify-between items-center pt-4 border-t border-border-subtle text-[12px] text-text-muted pl-2">
                                <div className="flex items-center gap-1.5">
                                    <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                                    {new Date(item.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                </div>
                                <span className="font-medium">{item.source} · {text.readMore}</span>
                            </div>
                            </div>
                        </a>
                    ))}
                </div>
            )}
        </div>
    );
}
