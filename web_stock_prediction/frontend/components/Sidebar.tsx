"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
    {
        href: "/",
        label: "Overview",
        icon: (
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M3 12 12 4l9 8" />
                <path d="M5 10v10h14V10" />
            </svg>
        ),
    },
    {
        href: "/predictions",
        label: "Predictions",
        icon: (
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
        ),
    },
];

export default function Sidebar() {
    const pathname = usePathname();

    const isActive = (href: string) => {
        if (href === "/") {
            return pathname === "/" || pathname === "/about";
        }

        return pathname === href;
    };

    return (
        <aside className="hidden min-h-screen w-[220px] min-w-[220px] border-r border-border-subtle bg-white p-0 md:flex md:flex-col">
            <Link href="/" className="flex items-center gap-[10px] border-b border-border-subtle px-5 py-[18px] text-[15px] font-bold tracking-[0.5px] text-text-primary transition-opacity hover:opacity-80">
                <svg className="shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="#15212f" />
                </svg>
                STOCK PREDICTOR
            </Link>
            <nav className="flex-1 py-3">
                {NAV_ITEMS.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`group flex items-center gap-3 border-l-[3px] border-transparent px-5 py-3 text-[13.5px] font-medium transition-all duration-200 ${isActive(item.href)
                            ? "border-accent-purple bg-slate-50 text-accent-purple"
                            : "text-text-secondary hover:border-accent-purple hover:bg-slate-50 hover:text-text-primary"
                            }`}
                    >
                        <span className={`opacity-70 group-hover:opacity-100 ${isActive(item.href) ? "opacity-100" : ""}`}>{item.icon}</span>
                        {item.label}
                    </Link>
                ))}
            </nav>
        </aside>
    );
}
