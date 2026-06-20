"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "stock_registration_token";
const EMAIL_KEY = "stock_registration_email";

type RegistrationContextValue = {
    isRegistered: boolean;
    email: string;
    loading: boolean;
    completeRegistration: (token: string, email: string) => void;
    logout: () => void;
};

const RegistrationContext = createContext<RegistrationContextValue | null>(null);

export function RegistrationProvider({ children }: { children: React.ReactNode }) {
    const [isRegistered, setIsRegistered] = useState(false);
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(true);

    const logout = useCallback(() => {
        window.localStorage.removeItem(TOKEN_KEY);
        window.localStorage.removeItem(EMAIL_KEY);
        setIsRegistered(false);
        setEmail("");
        window.dispatchEvent(new Event("stock-registration-change"));
    }, []);

    const completeRegistration = useCallback((token: string, registeredEmail: string) => {
        window.localStorage.setItem(TOKEN_KEY, token);
        window.localStorage.setItem(EMAIL_KEY, registeredEmail);
        setIsRegistered(true);
        setEmail(registeredEmail);
        window.dispatchEvent(new Event("stock-registration-change"));
    }, []);

    useEffect(() => {
        let ignore = false;
        const token = window.localStorage.getItem(TOKEN_KEY);
        const storedEmail = window.localStorage.getItem(EMAIL_KEY) || "";

        if (!token) {
            setLoading(false);
            return;
        }

        fetch(`${API_BASE_URL}/api/registration/status`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((response) => response.ok ? response.json() : { registered: false })
            .then((payload: { registered?: boolean; email?: string | null }) => {
                if (ignore) return;
                if (payload.registered) {
                    setIsRegistered(true);
                    setEmail(payload.email || storedEmail);
                } else {
                    logout();
                }
            })
            .catch(() => {
                if (!ignore) {
                    setIsRegistered(Boolean(token));
                    setEmail(storedEmail);
                }
            })
            .finally(() => {
                if (!ignore) setLoading(false);
            });

        return () => {
            ignore = true;
        };
    }, [logout]);

    const value = useMemo(
        () => ({ isRegistered, email, loading, completeRegistration, logout }),
        [isRegistered, email, loading, completeRegistration, logout]
    );

    return <RegistrationContext.Provider value={value}>{children}</RegistrationContext.Provider>;
}

export function useRegistration() {
    const context = useContext(RegistrationContext);
    if (!context) {
        throw new Error("useRegistration must be used inside RegistrationProvider");
    }
    return context;
}
