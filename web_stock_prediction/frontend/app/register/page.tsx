"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { useRegistration } from "@/components/RegistrationProvider";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const MESSAGE_TEXT = {
    en: {
        codeSent: "A verification code has been sent to your email.",
        genericError: "Unable to process the request.",
    },
    vi: {
        codeSent: "Mã xác minh đã được gửi tới email của bạn.",
        genericError: "Không thể xử lý yêu cầu.",
    },
};

export default function RegisterPage() {
    const router = useRouter();
    const { language } = useLanguage();
    const { completeRegistration } = useRegistration();
    const [email, setEmail] = useState("");
    const [code, setCode] = useState("");
    const [step, setStep] = useState<"email" | "code" | "success">("email");
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    const text = language === "vi"
        ? {
            eyebrow: "ĐĂNG KÝ NHẬN TÍN HIỆU",
            title: "Xác minh email để mở khóa thêm mã",
            description: "Nhập email của bạn. Chúng tôi sẽ gửi một mã gồm 6 chữ số để xác minh đăng ký.",
            emailLabel: "Email",
            emailPlaceholder: "you@example.com",
            sendCode: "Gửi mã xác minh",
            codeLabel: "Mã xác minh",
            codePlaceholder: "000000",
            verify: "Xác minh và đăng ký",
            resend: "Gửi lại mã",
            changeEmail: "Dùng email khác",
            sentTo: "Mã đã được gửi tới",
            successTitle: "Đăng ký thành công",
            successDescription: "Email của bạn đã được xác minh. Bạn có thể xem thêm các mã dự báo.",
            openPredictions: "Xem dự báo",
            benefitOne: "Nhận tín hiệu MUA/BÁN mới",
            benefitTwo: "Mở khóa thêm mã cổ phiếu",
        }
        : {
            eyebrow: "SIGNAL REGISTRATION",
            title: "Verify your email to unlock more symbols",
            description: "Enter your email and we will send a six-digit verification code.",
            emailLabel: "Email",
            emailPlaceholder: "you@example.com",
            sendCode: "Send verification code",
            codeLabel: "Verification code",
            codePlaceholder: "000000",
            verify: "Verify and register",
            resend: "Resend code",
            changeEmail: "Use another email",
            sentTo: "We sent a code to",
            successTitle: "Registration complete",
            successDescription: "Your email is verified. You can now view more prediction symbols.",
            openPredictions: "View predictions",
            benefitOne: "Receive new BUY/SELL signals",
            benefitTwo: "Unlock more stock symbols",
        };

    const readError = async (response: Response) => {
        try {
            const payload = await response.json() as { detail?: string };
            return payload.detail || "Không thể xử lý yêu cầu.";
        } catch {
            return "Không thể xử lý yêu cầu.";
        }
    };

    const readLocalizedError = async (response: Response) => {
        if (language === "vi") return readError(response);
        if (response.status === 429) return "Please wait before requesting or entering another code.";
        if (response.status === 422) return "Please check the email address or verification code.";
        if (response.status === 503) return "Unable to send the verification email. Please try again later.";
        if (response.status === 400) return "The verification code is incorrect or has expired.";
        return MESSAGE_TEXT.en.genericError;
    };

    const requestCode = async (event?: FormEvent) => {
        event?.preventDefault();
        setLoading(true);
        setError("");
        setMessage("");

        try {
            const response = await fetch(`${API_BASE_URL}/api/registration/request-code`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, language }),
            });
            if (!response.ok) {
                throw new Error(await readLocalizedError(response));
            }
            await response.json();
            setMessage(MESSAGE_TEXT[language].codeSent);
            setStep("code");
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : "Không thể gửi mã xác minh.");
        } finally {
            setLoading(false);
        }
    };

    const verifyCode = async (event: FormEvent) => {
        event.preventDefault();
        setLoading(true);
        setError("");
        setMessage("");

        try {
            const response = await fetch(`${API_BASE_URL}/api/registration/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, code, language }),
            });
            if (!response.ok) {
                throw new Error(await readLocalizedError(response));
            }
            const payload = await response.json() as {
                access_token: string;
                email: string;
                message: string;
            };
            completeRegistration(payload.access_token, payload.email);
            router.replace("/");
        } catch (verifyError) {
            setError(verifyError instanceof Error ? verifyError.message : "Không thể xác minh mã.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mx-auto flex w-full max-w-7xl flex-1 items-center px-4 py-10 sm:px-6 lg:px-8">
            <div className="grid w-full overflow-hidden rounded-2xl border border-border-subtle bg-white shadow-[0_20px_60px_rgba(21,33,47,0.12)] lg:grid-cols-[0.9fr_1.1fr]">
                <section className="bg-accent-gradient px-6 py-9 text-white sm:px-10 lg:px-12 lg:py-14">
                    <p className="text-xs font-bold tracking-[0.18em] text-emerald-300">{text.eyebrow}</p>
                    <h1 className="mt-4 max-w-md text-3xl font-black leading-tight sm:text-4xl">{text.title}</h1>
                    <div className="mt-8 space-y-4 text-sm font-semibold text-slate-100">
                        {[text.benefitOne, text.benefitTwo].map((benefit) => (
                            <div key={benefit} className="flex items-center gap-3">
                                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-buy text-white">
                                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                                        <path d="M4 10.5L8 14.5L16 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                </span>
                                <span>{benefit}</span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="flex min-h-[430px] items-center px-6 py-9 sm:px-10 lg:px-14">
                    <div className="w-full max-w-md">
                        {step === "success" ? (
                            <div className="text-center">
                                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-buy/10 text-buy">
                                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path d="M5 12.5L9.2 17L19 7" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                </div>
                                <h2 className="mt-5 text-2xl font-black text-text-primary">{text.successTitle}</h2>
                                <p className="mt-3 text-sm leading-6 text-text-secondary">{text.successDescription}</p>
                                <button
                                    type="button"
                                    onClick={() => router.replace("/")}
                                    className="mt-7 inline-flex h-11 items-center justify-center rounded-lg bg-buy px-6 text-sm font-bold text-white transition-colors hover:bg-emerald-700"
                                >
                                    {text.openPredictions}
                                </button>
                            </div>
                        ) : step === "email" ? (
                            <form onSubmit={requestCode}>
                                <label className="text-sm font-bold text-text-primary" htmlFor="registration-email">
                                    {text.emailLabel}
                                </label>
                                <input
                                    id="registration-email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    value={email}
                                    onChange={(event) => setEmail(event.target.value)}
                                    placeholder={text.emailPlaceholder}
                                    className="mt-2 h-12 w-full rounded-lg border border-border-subtle bg-slate-50 px-4 text-sm text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-buy focus:bg-white"
                                />
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="mt-4 flex h-12 w-full items-center justify-center rounded-lg bg-buy px-5 text-sm font-bold text-white transition-all hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {loading ? "..." : text.sendCode}
                                </button>
                            </form>
                        ) : (
                            <form onSubmit={verifyCode}>
                                <p className="mb-5 text-sm leading-6 text-text-secondary">
                                    {text.sentTo} <strong className="text-text-primary">{email}</strong>
                                </p>
                                <label className="text-sm font-bold text-text-primary" htmlFor="registration-code">
                                    {text.codeLabel}
                                </label>
                                <input
                                    id="registration-code"
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    required
                                    maxLength={6}
                                    pattern="[0-9]{6}"
                                    value={code}
                                    onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                                    placeholder={text.codePlaceholder}
                                    className="mt-2 h-14 w-full rounded-lg border border-border-subtle bg-slate-50 px-4 text-center text-2xl font-black tracking-[0.35em] text-text-primary outline-none transition-colors placeholder:tracking-[0.35em] placeholder:text-text-muted focus:border-buy focus:bg-white"
                                />
                                <button
                                    type="submit"
                                    disabled={loading || code.length !== 6}
                                    className="mt-4 flex h-12 w-full items-center justify-center rounded-lg bg-buy px-5 text-sm font-bold text-white transition-all hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {loading ? "..." : text.verify}
                                </button>
                                <div className="mt-4 flex items-center justify-between gap-4 text-xs font-semibold">
                                    <button type="button" disabled={loading} onClick={() => requestCode()} className="text-buy hover:underline disabled:opacity-50">
                                        {text.resend}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setCode("");
                                            setError("");
                                            setMessage("");
                                            setStep("email");
                                        }}
                                        className="text-text-secondary hover:text-text-primary"
                                    >
                                        {text.changeEmail}
                                    </button>
                                </div>
                            </form>
                        )}

                        {error && (
                            <p className="mt-4 rounded-lg border border-sell/20 bg-sell/5 px-4 py-3 text-sm font-semibold text-sell">
                                {error}
                            </p>
                        )}
                        {message && step !== "success" && (
                            <p className="mt-4 rounded-lg border border-buy/20 bg-buy/5 px-4 py-3 text-sm font-semibold text-buy">
                                {step === "code" ? MESSAGE_TEXT[language].codeSent : message}
                            </p>
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
}
