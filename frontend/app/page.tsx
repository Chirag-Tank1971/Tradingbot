"use client";

import {
  Activity,
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Loader2,
  Send,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

type OrderSide = "BUY" | "SELL";
type OrderType = "MARKET" | "LIMIT";

type OrderResult = {
  order_id: string;
  status: string;
  executed_qty: string;
  average_price: string;
  client_order_id: string;
};

type ApiResponse = {
  success: boolean;
  error?: string;
  order?: OrderResult;
};

const initialForm = {
  symbol: "BTCUSDT",
  side: "BUY" as OrderSide,
  type: "MARKET" as OrderType,
  quantity: "0.001",
  price: "",
};

import TradingChart, { ChartMarker } from "./components/TradingChart";

export default function TradingPage() {
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<OrderResult | null>(null);
  const [chartMarkers, setChartMarkers] = useState<ChartMarker[]>([]);

  const requestPreview = useMemo(
    () => [
      ["Symbol", form.symbol || "-"],
      ["Side", form.side],
      ["Type", form.type],
      ["Quantity", form.quantity || "-"],
      ...(form.type === "LIMIT" ? [["Price", form.price || "-"]] : []),
    ],
    [form],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");
    setResult(null);

    const payload = {
      symbol: form.symbol.trim(),
      side: form.side,
      type: form.type,
      quantity: form.quantity.trim(),
      price: form.type === "LIMIT" ? form.price.trim() : undefined,
    };

    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await response.json()) as ApiResponse;

      if (!response.ok || !data.success || !data.order) {
        setError(data.error || "Order failed.");
        return;
      }

      setResult(data.order);
      const nowSec = Math.floor(Date.now() / 1000);
      setChartMarkers((prev) => [
        ...prev,
        {
          time: nowSec,
          position: form.side === "BUY" ? "belowBar" : "aboveBar",
          color: form.side === "BUY" ? "#0c9b6d" : "#d94a4a",
          shape: form.side === "BUY" ? "arrowUp" : "arrowDown",
          text: `${form.side} ${data.order?.executed_qty || form.quantity}`,
        },
      ]);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Request failed.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="dashboardShell">
      <section className="dashboardFrame wideFrame">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">Binance Futures Testnet</p>
            <h1>Terminal & Order Ticket</h1>
          </div>
          <nav className="topNav" aria-label="Primary navigation">
            <Link className="active" href="/">
              Order Ticket
            </Link>
            <Link href="/bot">Automated Bot</Link>
            <Link href="/backtest">Backtesting</Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </header>

        {/* Live Candlestick Chart */}
        <section style={{ padding: "0 28px 24px" }}>
          <TradingChart
            symbol={form.symbol}
            onSymbolChange={(sym) => setForm((curr) => ({ ...curr, symbol: sym }))}
            markers={chartMarkers}
            height={380}
          />
        </section>

        <section className="orderWorkspace" aria-label="Trading workspace">
          <section className="dataPanel orderPanel" aria-labelledby="ticket-title">
            <div className="panelTitle">
              <div>
                <p className="eyebrow">New Order</p>
                <h2 id="ticket-title">Trade Details</h2>
              </div>
              <span>USDT-M</span>
            </div>
          <form className="orderForm" onSubmit={handleSubmit}>
            <label className="field">
              <span>Symbol</span>
              <input
                value={form.symbol}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    symbol: event.target.value.toUpperCase(),
                  }))
                }
                autoComplete="off"
                spellCheck={false}
              />
            </label>

            <div className="field">
              <span>Side</span>
              <div className="segmentGrid">
                <button
                  className={form.side === "BUY" ? "segment activeBuy" : "segment"}
                  type="button"
                  onClick={() => setForm((current) => ({ ...current, side: "BUY" }))}
                >
                  <ArrowUp size={17} aria-hidden="true" />
                  BUY
                </button>
                <button
                  className={
                    form.side === "SELL" ? "segment activeSell" : "segment"
                  }
                  type="button"
                  onClick={() => setForm((current) => ({ ...current, side: "SELL" }))}
                >
                  <ArrowDown size={17} aria-hidden="true" />
                  SELL
                </button>
              </div>
            </div>

            <div className="field">
              <span>Type</span>
              <div className="segmentGrid">
                <button
                  className={form.type === "MARKET" ? "segment activeNeutral" : "segment"}
                  type="button"
                  onClick={() =>
                    setForm((current) => ({ ...current, type: "MARKET" }))
                  }
                >
                  MARKET
                </button>
                <button
                  className={form.type === "LIMIT" ? "segment activeNeutral" : "segment"}
                  type="button"
                  onClick={() =>
                    setForm((current) => ({ ...current, type: "LIMIT" }))
                  }
                >
                  LIMIT
                </button>
              </div>
            </div>

            <label className="field">
              <span>Quantity</span>
              <input
                value={form.quantity}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    quantity: event.target.value,
                  }))
                }
                inputMode="decimal"
                autoComplete="off"
              />
            </label>

            {form.type === "LIMIT" ? (
              <label className="field">
                <span>Price</span>
                <input
                  value={form.price}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      price: event.target.value,
                    }))
                  }
                  inputMode="decimal"
                  autoComplete="off"
                />
              </label>
            ) : null}

            <button className="submitButton" type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="spin" size={18} aria-hidden="true" />
              ) : (
                <Send size={18} aria-hidden="true" />
              )}
              {isSubmitting ? "Submitting" : "Submit Order"}
            </button>
          </form>
        </section>

          <section className="dataPanel orderPanel" aria-label="Order details">
            <div className="panelTitle">
              <div>
                <p className="eyebrow">Current Request</p>
                <h2>{form.symbol || "Symbol"}</h2>
              </div>
              <span className={form.side === "BUY" ? "sideBadge buy" : "sideBadge sell"}>
                {form.side}
              </span>
            </div>

          <div className="previewTable">
            {requestPreview.map(([label, value]) => (
              <div className="previewRow" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          <div className="resultArea">
            {result ? (
              <div className="successBox">
                <div className="resultTitle">
                  <CheckCircle2 size={20} aria-hidden="true" />
                  <span>Order Successful</span>
                </div>
                <ResultRows result={result} />
              </div>
            ) : null}

            {error ? (
              <div className="errorBox">
                <div className="resultTitle">
                  <AlertCircle size={20} aria-hidden="true" />
                  <span>Order Failed</span>
                </div>
                <p>{error}</p>
              </div>
            ) : null}

            {!result && !error ? (
              <div className="emptyState">
                <Activity size={22} aria-hidden="true" />
                <span>Ready</span>
              </div>
            ) : null}
          </div>
        </section>
        </section>
      </section>
    </main>
  );
}

function ResultRows({ result }: { result: OrderResult }) {
  const rows = [
    ["Order ID", result.order_id],
    ["Status", result.status],
    ["Executed Qty", result.executed_qty],
    ["Average Price", result.average_price],
    ["Client Order ID", result.client_order_id],
  ];

  return (
    <div className="resultRows">
      {rows.map(([label, value]) => (
        <div className="previewRow" key={label}>
          <span>{label}</span>
          <strong>{value || "-"}</strong>
        </div>
      ))}
    </div>
  );
}
