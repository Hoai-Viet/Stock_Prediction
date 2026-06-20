"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { useRegistration } from "@/components/RegistrationProvider";
import vietnamFlag from "@/logo/vietnam.png";
import unitedKingdomFlag from "@/logo/united-kingdom.png";

type SearchSymbol = {
    symbol_key: number;
    symbol_code: string;
    company_name?: string | null;
    sector_name?: string | null;
    description?: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const SYMBOL_ALIASES: Record<string, string[]> = {
    ACB: ["asia commercial bank"],
    BAB: ["bac a bank"],
    BID: ["bidv", "bank for investment and development", "investment and development of vietnam"],
    CTG: ["vietinbank", "vietnam joint stock commercial bank for industry and trade"],
    EIB: ["eximbank", "vietnam export import bank"],
    HDB: ["hdbank", "ho chi minh city development bank"],
    LPB: ["lpbank", "lienvietpostbank", "lien viet post bank"],
    MBB: ["mbbank", "military bank", "mb bank"],
    MSB: ["maritime bank"],
    NAB: ["nam a bank"],
    NVB: ["ncb", "navibank", "national citizen bank"],
    OCB: ["orient commercial bank"],
    PGB: ["pgbank", "petrolimex bank"],
    SGB: ["saigonbank", "sai gon bank"],
    SHB: ["saigon hanoi bank"],
    SSB: ["seabank", "southeast asia bank"],
    STB: ["sacombank", "sai gon thuong tin"],
    TCB: ["techcombank", "technological and commercial bank"],
    TPB: ["tpbank", "tien phong bank"],
    VAB: ["viet a bank"],
    VCB: ["vietcombank", "foreign trade bank"],
    VIB: ["vietnam international bank"],
    VPB: ["vpbank", "vietnam prosperity bank"],
};

const NAV_ITEMS = [
    { href: "/", label: { en: "Overview", vi: "Tổng quan" } },
    { href: "/predictions", label: { en: "Predictions", vi: "Dự báo" } },
    { href: "/about", label: { en: "About", vi: "Giới thiệu" } },
];

const UI_TEXT = {
    en: {
        searchPlaceholder: "Search symbol",
        register: "Register",
        languageLabel: "Switch to Vietnamese",
        noResult: "No matching symbol found.",
        stockSymbol: "Stock symbol",
    },
    vi: {
        searchPlaceholder: "Tìm mã cổ phiếu",
        register: "Đăng ký",
        languageLabel: "Switch to English",
        noResult: "Không tìm thấy mã phù hợp.",
        stockSymbol: "Mã cổ phiếu",
    },
};

const ACCOUNT_TEXT = {
    en: { account: "Account", logout: "Log out" },
    vi: { account: "Tài khoản", logout: "Đăng xuất" },
};

const getSearchText = (symbol: SearchSymbol) =>
    [
        symbol.symbol_code,
        symbol.company_name,
        symbol.sector_name,
        symbol.description,
        ...(SYMBOL_ALIASES[symbol.symbol_code] || []),
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

export default function Topbar() {
    const pathname = usePathname();
    const router = useRouter();
    const { language, toggleLanguage } = useLanguage();
    const { isRegistered, email, logout } = useRegistration();
    const [query, setQuery] = useState("");
    const [symbols, setSymbols] = useState<SearchSymbol[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [isAccountOpen, setIsAccountOpen] = useState(false);

    useEffect(() => {
        let ignore = false;

        fetch(`${API_BASE_URL}/api/predictions/symbols`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error("Failed to load symbols");
                }
                return res.json();
            })
            .then((data: SearchSymbol[]) => {
                if (!ignore) {
                    setSymbols(data.filter((item) => item.symbol_code));
                }
            })
            .catch(() => {
                if (!ignore) {
                    setSymbols([]);
                }
            });

        return () => {
            ignore = true;
        };
    }, []);

    const searchResults = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        if (!normalizedQuery) return [];

        return symbols
            .filter((symbol) => getSearchText(symbol).includes(normalizedQuery))
            .slice(0, 6);
    }, [query, symbols]);

    const selectSymbol = (symbolCode: string) => {
        const normalizedSymbol = symbolCode.toUpperCase();
        setQuery("");
        setIsOpen(false);

        if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("stock-symbol-select", { detail: normalizedSymbol }));
        }

        router.push(`/predictions?symbol=${encodeURIComponent(normalizedSymbol)}`);
    };

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (searchResults.length > 0) {
            selectSymbol(searchResults[0].symbol_code);
        }
    };

    return (
        <header className="relative z-[100] border-b border-border-subtle bg-white/95 backdrop-blur-[10px]">
            <div className="mx-auto flex min-h-[64px] max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
                <Link
                    href="/"
                    className="flex items-center gap-2 text-[13px] font-medium tracking-[0.16em] text-text-primary transition-opacity hover:opacity-80"
                >
                    <svg className="shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="#15212f" />
                    </svg>
                    STOCK PREDICTOR
                </Link>

                <nav className="flex items-center gap-2">
                    {NAV_ITEMS.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`rounded px-3 py-2 text-[13px] font-medium transition-colors ${((item.href === "/" && pathname === "/") || pathname === item.href)
                                ? "bg-buy/10 text-buy"
                                : "text-text-secondary hover:bg-slate-50 hover:text-text-primary"
                                }`}
                        >
                            {item.label[language]}
                        </Link>
                    ))}
                </nav>

                <form className="relative min-w-[220px] flex-1 lg:max-w-[430px]" onSubmit={handleSubmit}>
                    <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        className="w-full rounded-lg border border-border-subtle bg-slate-50 py-2 pl-[36px] pr-[14px] text-[13px] text-text-primary outline-none transition-colors duration-200 placeholder:text-text-muted focus:border-accent-purple"
                        type="text"
                        placeholder={UI_TEXT[language].searchPlaceholder}
                        value={query}
                        onChange={(event) => {
                            setQuery(event.target.value);
                            setIsOpen(true);
                        }}
                        onFocus={() => setIsOpen(true)}
                        onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
                    />

                    {isOpen && query.trim() && (
                        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-[120] max-h-[320px] overflow-y-auto rounded-lg border border-border-subtle bg-white shadow-2xl shadow-slate-200/70">
                            {searchResults.length > 0 ? (
                                searchResults.map((symbol) => (
                                    <button
                                        key={symbol.symbol_code}
                                        type="button"
                                        onMouseDown={(event) => event.preventDefault()}
                                        onClick={() => selectSymbol(symbol.symbol_code)}
                                        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-slate-50"
                                    >
                                        <span className="flex h-8 min-w-10 items-center justify-center rounded-md border border-border-subtle bg-slate-50 text-[12px] font-bold text-accent-purple">
                                            {symbol.symbol_code}
                                        </span>
                                        <span className="min-w-0">
                                            <span className="block truncate text-[13px] font-semibold text-text-primary">
                                                {symbol.company_name || symbol.symbol_code}
                                            </span>
                                            <span className="block truncate text-[11px] text-text-muted">
                                                {symbol.sector_name || UI_TEXT[language].stockSymbol}
                                            </span>
                                        </span>
                                    </button>
                                ))
                            ) : (
                                <div className="px-3 py-3 text-[12px] text-text-muted">{UI_TEXT[language].noResult}</div>
                            )}
                        </div>
                    )}
                </form>

                <div className="ml-auto flex items-center gap-2 sm:gap-4">
                    <button
                        type="button"
                        onClick={toggleLanguage}
                        className="inline-flex h-10 w-14 items-center justify-center overflow-hidden rounded-md border-0 bg-transparent p-0 shadow-none outline-none transition-all hover:-translate-y-0.5 hover:bg-slate-100"
                        title={UI_TEXT[language].languageLabel}
                        aria-label={UI_TEXT[language].languageLabel}
                    >
                        <img
                            src={language === "en" ? vietnamFlag.src : unitedKingdomFlag.src}
                            alt=""
                            aria-hidden="true"
                            className="h-7 w-10 rounded-sm object-cover"
                        />
                    </button>
                    <button className="inline-flex h-10 w-10 items-center justify-center rounded-md border-0 bg-transparent p-0 text-text-secondary shadow-none outline-none transition-colors duration-200 hover:bg-slate-100 hover:text-text-primary" title="Notifications">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                        </svg>
                    </button>
                    {isRegistered ? (
                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setIsAccountOpen((current) => !current)}
                                onBlur={() => window.setTimeout(() => setIsAccountOpen(false), 120)}
                                className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-buy text-white transition-colors hover:bg-emerald-700"
                                aria-label={ACCOUNT_TEXT[language].account}
                                aria-expanded={isAccountOpen}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                    <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                                    <path d="M4.5 20C5.5 15.8 8 14 12 14C16 14 18.5 15.8 19.5 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                </svg>
                            </button>
                            {isAccountOpen && (
                                <div className="absolute right-0 top-[calc(100%+8px)] z-[130] w-64 overflow-hidden rounded-xl border border-border-subtle bg-white shadow-[0_16px_38px_rgba(21,33,47,0.16)]">
                                    <div className="border-b border-border-subtle px-4 py-3">
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                                            {ACCOUNT_TEXT[language].account}
                                        </p>
                                        <p className="mt-1 truncate text-sm font-semibold text-text-primary">{email}</p>
                                    </div>
                                    <button
                                        type="button"
                                        onMouseDown={(event) => event.preventDefault()}
                                        onClick={() => {
                                            setIsAccountOpen(false);
                                            logout();
                                            router.push("/");
                                        }}
                                        className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-sell transition-colors hover:bg-sell/5"
                                    >
                                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                            <path d="M10 5H5V19H10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                            <path d="M14 8L18 12L14 16M18 12H9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                        {ACCOUNT_TEXT[language].logout}
                                    </button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <Link
                            href="/register"
                            className="inline-flex h-8 items-center justify-center rounded-full bg-accent-gradient px-4 text-[12px] font-bold text-white transition-opacity hover:opacity-90"
                        >
                            {UI_TEXT[language].register}
                        </Link>
                    )}
                </div>
            </div>
        </header>
    );
}
