import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                'bg-primary': '#f6f8fb',
                'bg-secondary': '#edf2f7',
                'bg-card': '#ffffff',
                'border-subtle': '#d9e0ea',
                'border-glow': 'rgba(21, 33, 47, 0.18)',
                'accent-purple': '#15212f',
                'accent-blue': '#526173',
                'buy': '#0f9f6e',
                'sell': '#df3d3d',
                'hold': '#d99a16',
                'silent': '#7b8794',
                'text-primary': '#15212f',
                'text-secondary': '#526173',
                'text-muted': '#7b8794',
            },
            backgroundImage: {
                'accent-gradient': 'linear-gradient(135deg, #15212f, #526173)',
            }
        },
    },
    plugins: [],
};
export default config;
