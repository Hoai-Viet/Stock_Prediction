import type { Metadata } from "next";
import "./globals.css";
import Topbar from "@/components/Topbar";
import Footer from "@/components/Footer";
import { LanguageProvider } from "@/components/LanguageProvider";

export const metadata: Metadata = {
    title: "STOCK PREDICTOR",
    description: "AI-powered Vietnamese stock prediction terminal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body>
                <LanguageProvider>
                    <div className="flex min-h-screen flex-col bg-gradient-to-br from-bg-primary to-bg-secondary">
                        <Topbar />
                        <main className="flex-1">{children}</main>
                        <Footer />
                    </div>
                </LanguageProvider>
            </body>
        </html>
    );
}
