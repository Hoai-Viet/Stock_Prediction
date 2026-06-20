import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

function formatChartTime(time: any, period: string) {
    const rawDate = typeof time === "object" && time !== null
        ? `${time.year}-${String(time.month).padStart(2, "0")}-${String(time.day).padStart(2, "0")}`
        : String(time);
    const date = new Date(rawDate);

    if (Number.isNaN(date.getTime())) return rawDate;
    if (period === "1Y") return String(date.getFullYear());
    if (period !== "1D") return `${String(date.getMonth() + 1).padStart(2, "0")}/${date.getFullYear()}`;
    return `${String(date.getDate()).padStart(2, "0")}/${String(date.getMonth() + 1).padStart(2, "0")}/${date.getFullYear()}`;
}

export default function CandleChart({ data, period = "1D" }: { data: any[]; period?: string }) {
    const chartContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#526173',
            },
            grid: {
                vertLines: { color: '#e7edf4' },
                horzLines: { color: '#e7edf4' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            crosshair: {
                mode: 1, // CrosshairMode.Normal
            },
            rightPriceScale: {
                borderColor: '#d9e0ea',
            },
            timeScale: {
                borderColor: '#d9e0ea',
                barSpacing: 14,
                minBarSpacing: 8,
                tickMarkFormatter: (time: any) => formatChartTime(time, period),
            },
            localization: {
                timeFormatter: (time: any) => formatChartTime(time, period),
            },
            handleScroll: {
                mouseWheel: false,
            },
            handleScale: {
                mouseWheel: true,
            },
        });

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#0f9f6e',
            downColor: '#df3d3d',
            borderVisible: false,
            wickUpColor: '#0f9f6e',
            wickDownColor: '#df3d3d',
        });

        candlestickSeries.setData(data);
        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data]);

    return <div ref={chartContainerRef} className="w-full h-full" />;
}
