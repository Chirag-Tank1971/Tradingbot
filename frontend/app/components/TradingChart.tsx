"use client";

import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  Time,
  createChart,
  createSeriesMarkers,
} from "lightweight-charts";
import { Activity, Clock, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type ChartMarker = {
  time: number;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown" | "circle";
  text: string;
};

type CandleData = {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type TradingChartProps = {
  symbol?: string;
  onSymbolChange?: (symbol: string) => void;
  markers?: ChartMarker[];
  height?: number;
};

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"];

export default function TradingChart({
  symbol: initialSymbol = "BTCUSDT",
  onSymbolChange,
  markers = [],
  height = 420,
}: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const [symbol, setSymbol] = useState(initialSymbol);
  const [interval, setInterval] = useState("1h");
  const [isLoading, setIsLoading] = useState(true);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceChangePct, setPriceChangePct] = useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    setSymbol(initialSymbol);
  }, [initialSymbol]);

  const markersPrimitiveRef = useRef<any>(null);

  // Initialize Lightweight Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: "#161d22" },
        textColor: "#8b9aa8",
        fontSize: 12,
        fontFamily: "Inter, -apple-system, sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.05)" },
        horzLines: { color: "rgba(255, 255, 255, 0.05)" },
      },
      crosshair: {
        mode: 1,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "rgba(255, 255, 255, 0.12)",
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.12)",
        autoScale: true,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#0c9b6d",
      downColor: "#d94a4a",
      borderVisible: false,
      wickUpColor: "#0c9b6d",
      wickDownColor: "#d94a4a",
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "rgba(22, 163, 184, 0.4)",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "volume",
    });

    chart.priceScale("volume").applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    markersPrimitiveRef.current = null;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      markersPrimitiveRef.current = null;
    };
  }, [height]);

  // Fetch candle data
  const loadKlines = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(
        `/api/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=300`,
      );
      const json = await res.json();

      if (json.candles && candleSeriesRef.current && volumeSeriesRef.current) {
        const rawCandles: CandleData[] = json.candles;

        const candleData = rawCandles.map((c) => ({
          time: c.timestamp as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));

        const volumeData = rawCandles.map((c) => ({
          time: c.timestamp as Time,
          value: c.volume,
          color: c.close >= c.open ? "rgba(12, 155, 109, 0.35)" : "rgba(217, 74, 74, 0.35)",
        }));

        candleSeriesRef.current.setData(candleData);
        volumeSeriesRef.current.setData(volumeData);

        if (rawCandles.length > 0) {
          const last = rawCandles[rawCandles.length - 1];
          const first = rawCandles[0];
          setCurrentPrice(last.close);
          const chg = ((last.close - first.open) / first.open) * 100;
          setPriceChangePct(chg);
          setLastUpdated(new Date().toLocaleTimeString());
        }

        // Apply trade markers if provided
        if (markers.length > 0 && candleSeriesRef.current) {
          const validMarkers = markers
            .filter((m) => m.time >= rawCandles[0].timestamp && m.time <= rawCandles[rawCandles.length - 1].timestamp)
            .map((m) => ({
              time: m.time as Time,
              position: m.position,
              color: m.color,
              shape: m.shape,
              text: m.text,
            }));
          try {
            if (!markersPrimitiveRef.current) {
              markersPrimitiveRef.current = createSeriesMarkers(candleSeriesRef.current, validMarkers);
            } else {
              markersPrimitiveRef.current.setMarkers(validMarkers);
            }
          } catch {
            // Ignore marker timestamp boundary mismatch
          }
        }
      }
    } catch (err) {
      console.error("Failed to load klines:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadKlines();
    const timer = window.setInterval(loadKlines, 8000); // 8s live refresh
    return () => window.clearInterval(timer);
  }, [symbol, interval]);

  const handleSelectSymbol = (sym: string) => {
    setSymbol(sym);
    if (onSymbolChange) {
      onSymbolChange(sym);
    }
  };

  return (
    <div className="chartWrapper">
      <div className="chartHeader">
        <div className="chartSymbolMeta">
          <select
            value={symbol}
            onChange={(e) => handleSelectSymbol(e.target.value)}
            className="chartSymbolSelect"
          >
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          {currentPrice !== null && (
            <div className="chartPriceLive">
              <span className="livePriceVal">${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              {priceChangePct !== null && (
                <span className={`livePriceChg ${priceChangePct >= 0 ? "positive" : "negative"}`}>
                  {priceChangePct >= 0 ? "+" : ""}
                  {priceChangePct.toFixed(2)}%
                </span>
              )}
            </div>
          )}
        </div>

        <div className="chartControls">
          <div className="timeframeButtons">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setInterval(tf)}
                className={`tfButton ${interval === tf ? "active" : ""}`}
              >
                {tf}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={loadKlines}
            className="refreshChartBtn"
            title="Refresh Chart"
            disabled={isLoading}
          >
            <RefreshCw size={14} className={isLoading ? "spin" : ""} />
          </button>
        </div>
      </div>

      <div className="chartCanvasWrapper">
        <div className="chartCanvasContainer" ref={chartContainerRef} />
        {isLoading && !currentPrice && (
          <div className="chartLoadingOverlay">
            <Activity className="spin" size={24} />
            <span>Loading market data...</span>
          </div>
        )}
      </div>

      <div className="chartFooter">
        <div className="chartNotice">
          <Clock size={12} />
          <span>Binance Futures {interval} interval • Auto-refresh 8s</span>
        </div>
        {lastUpdated && <span>Updated {lastUpdated}</span>}
      </div>
    </div>
  );
}
