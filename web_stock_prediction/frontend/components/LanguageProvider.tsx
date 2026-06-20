"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Language = "en" | "vi";

type LanguageContextValue = {
    language: Language;
    setLanguage: (language: Language) => void;
    toggleLanguage: () => void;
};

const LANGUAGE_STORAGE_KEY = "stock-ui-language";

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguageState] = useState<Language>("en");

    useEffect(() => {
        const savedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
        if (savedLanguage === "en" || savedLanguage === "vi") {
            setLanguageState(savedLanguage);
        }
    }, []);

    const setLanguage = (nextLanguage: Language) => {
        setLanguageState(nextLanguage);
        window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
        document.documentElement.lang = nextLanguage;
    };

    const toggleLanguage = () => {
        setLanguage(language === "en" ? "vi" : "en");
    };

    useEffect(() => {
        document.documentElement.lang = language;
    }, [language]);

    const value = useMemo(
        () => ({ language, setLanguage, toggleLanguage }),
        [language]
    );

    return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (!context) {
        throw new Error("useLanguage must be used inside LanguageProvider");
    }
    return context;
}
