"use client";

import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Cpu,
  DollarSign,
  History,
  Layers,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Sliders,
  Terminal,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type BotPortfolio = {
  initial_capital: number;
  cash: number;
  position_qty: number;
  position_entry: number;
  position_time: string;
  position_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  total_portfolio_value: number;
  total_realized_pnl: number;
};

type BotTrade = {
  id: number;
  symbol: string;
  mode: string;
  side: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_pct: number;
  reason: string;
};

type BotLog = {
  timestamp: string;
  level: string;
  message: string;
};

type BotStatusResponse = {
  status: "STOPPED" | "RUNNING" | "ERROR";
  mode: "PAPER" | "TESTNET";
  symbol: string;
  interval: string;
  poll_interval: number;
  strategy_name: string;
  strategy_description: string;
  last_price: number;
  last_signal: "BUY" | "SELL" | "HOLD";
  last_signal_reason: string;
  last_tick_time: string;
  ticks_count: number;
  paper_portfolio: BotPortfolio;
  recent_trades: BotTrade[];
  recent_logs: BotLog[];
};

export default function BotPage() {
  const [data, setData] = useState<BotStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionPending, setIsActionPending] = useState(false);
  const [error, setError] = useState("");

  // Configuration form state
  const [mode, setMode] = useState<"PAPER" | "TESTNET">("PAPER");
  const [strategy, setStrategy] = useState("ema_rsi");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setInterval] = useState("1m");
  const [pollInterval, setPollInterval] = useState(15);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/bot/status");
      const json = await res.json();
      if (json.success && json.data) {
        setData(json.data);
      }
    } catch (err) {
      console.error("Failed to fetch bot status:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = window.setInterval(fetchStatus, 3000); // 3s polling for live activity
    return () => window.clearInterval(timer);
  }, []);

  const handleStart = async () => {
    setIsActionPending(true);
    setError("");
    try {
      const res = await fetch("/api/bot/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          strategy_name: strategy,
          symbol,
          interval,
          poll_interval: Number(pollInterval),
        }),
      });
      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error || json.detail || "Failed to start bot");
      }
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Start failed");
    } finally {
      setIsActionPending(false);
    }
  };

  const handleStop = async () => {
    setIsActionPending(true);
    setError("");
    try {
      const res = await fetch("/api/bot/stop", { method: "POST" });
      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error || json.detail || "Failed to stop bot");
      }
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stop failed");
    } finally {
      setIsActionPending(false);
    }
  };

  const handleManualTick = async () => {
    setIsActionPending(true);
    setError("");
    try {
      const res = await fetch("/api/bot/tick", { method: "POST" });
      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error || json.detail || "Tick evaluation failed");
      }
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tick failed");
    } finally {
      setIsActionPending(false);
    }
  };

  const handleResetPaper = async () => {
    if (!confirm("Reset paper trading portfolio back to $10,000?")) return;
    setIsActionPending(true);
    try {
      await fetch("/api/bot/reset", { method: "POST" });
      await fetchStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionPending(false);
    }
  };

  const isRunning = data?.status === "RUNNING";

  return (
    <main className="dashboardShell">
      <section className="dashboardFrame wideFrame">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">Autonomous Trading Engine</p>
            <h1>Strategy Bot Runner</h1>
          </div>
          <nav className="topNav" aria-label="Primary navigation">
            <Link href="/">Order Ticket</Link>
            <Link className="active" href="/bot">
              Automated Bot
            </Link>
            <Link href="/backtest">Backtesting</Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </header>

        {error && (
          <div className="callout error" style={{ margin: "16px 28px 0" }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Live Controller Bar */}
        <section className="botControlBar">
          <div className="botStatusHeader">
            <div className={`statusIndicator ${isRunning ? "running" : "stopped"}`}>
              <span className="pulseDot" />
              <span className="statusText">
                {isRunning ? "AUTOPILOT ACTIVE" : "BOT STOPPED"}
              </span>
            </div>

            <div className="badgeGroup">
              <span className={`modeBadge ${data?.mode === "TESTNET" ? "liveBadge" : "paperBadge"}`}>
                {data?.mode || mode} MODE
              </span>
              <span className="infoBadge">
                {data?.symbol || symbol} • {data?.interval || interval}
              </span>
              {data?.last_price ? (
                <span className="infoBadge priceBadge">
                  ${data.last_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              ) : null}
            </div>
          </div>

          <div className="botActionButtons">
            {isRunning ? (
              <button
                type="button"
                onClick={handleStop}
                disabled={isActionPending}
                className="controlBtn stopBtn"
              >
                <Pause size={16} />
                <span>Stop Autopilot</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStart}
                disabled={isActionPending}
                className="controlBtn startBtn"
              >
                <Play size={16} />
                <span>Start Autopilot</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleManualTick}
              disabled={isActionPending}
              className="controlBtn secondaryBtn"
              title="Execute a single evaluation step immediately"
            >
              <Zap size={16} />
              <span>Step Once</span>
            </button>

            <button
              type="button"
              onClick={handleResetPaper}
              disabled={isActionPending || isRunning}
              className="controlBtn secondaryBtn"
              title="Reset simulated portfolio"
            >
              <RotateCcw size={16} />
              <span>Reset Portfolio</span>
            </button>
          </div>
        </section>

        {/* Bot Workspace Grid */}
        <div className="botWorkspaceGrid">
          {/* Left Column: Metrics & Config */}
          <div className="botLeftCol">
            {/* Portfolio Status Cards */}
            <div className="metricsGrid">
              <div className="metricCard">
                <span className="metricLabel">Total Portfolio Value</span>
                <div className="metricValueRow">
                  <span className="metricVal">
                    ${data?.paper_portfolio.total_portfolio_value.toLocaleString() || "10,000.00"}
                  </span>
                </div>
                <span className="metricSub">
                  Cash Balance: ${data?.paper_portfolio.cash.toLocaleString() || "10,000.00"}
                </span>
              </div>

              <div className="metricCard">
                <span className="metricLabel">Total Realized PnL</span>
                <div className="metricValueRow">
                  <span
                    className={`metricVal ${
                      (data?.paper_portfolio.total_realized_pnl || 0) >= 0 ? "positive" : "negative"
                    }`}
                  >
                    {(data?.paper_portfolio.total_realized_pnl || 0) >= 0 ? "+" : ""}$
                    {data?.paper_portfolio.total_realized_pnl.toFixed(2) || "0.00"}
                  </span>
                </div>
                <span className="metricSub">
                  Completed Trades: {data?.recent_trades.length || 0}
                </span>
              </div>

              <div className="metricCard">
                <span className="metricLabel">Current Open Position</span>
                <div className="metricValueRow">
                  {data?.paper_portfolio.position_qty && data.paper_portfolio.position_qty > 0 ? (
                    <>
                      <span className="metricVal">
                        {data.paper_portfolio.position_qty} {data.symbol}
                      </span>
                      <span
                        className={`metricBadge ${
                          data.paper_portfolio.unrealized_pnl >= 0 ? "positive" : "negative"
                        }`}
                      >
                        {data.paper_portfolio.unrealized_pnl >= 0 ? "+" : ""}$
                        {data.paper_portfolio.unrealized_pnl.toFixed(2)}
                      </span>
                    </>
                  ) : (
                    <span className="metricVal neutralText">Flat (No Position)</span>
                  )}
                </div>
                <span className="metricSub">
                  {data?.paper_portfolio.position_entry
                    ? `Entry: $${data.paper_portfolio.position_entry.toLocaleString()}`
                    : "Waiting for buy trigger"}
                </span>
              </div>

              <div className="metricCard">
                <span className="metricLabel">Last Strategy Signal</span>
                <div className="metricValueRow">
                  <span
                    className={`metricVal ${
                      data?.last_signal === "BUY"
                        ? "positive"
                        : data?.last_signal === "SELL"
                        ? "negative"
                        : ""
                    }`}
                  >
                    {data?.last_signal || "HOLD"}
                  </span>
                  <span className="metricBadge neutral">
                    Tick #{data?.ticks_count || 0}
                  </span>
                </div>
                <span className="metricSub textEllipsis" title={data?.last_signal_reason}>
                  {data?.last_signal_reason || "Awaiting first tick"}
                </span>
              </div>
            </div>

            {/* Strategy Configuration Form */}
            <div className="dataPanel" style={{ marginTop: "20px" }}>
              <div className="panelTitle">
                <div>
                  <p className="eyebrow">Parameters</p>
                  <h3>Strategy Settings</h3>
                </div>
                <Sliders size={18} className="mutedIcon" />
              </div>

              <div className="configForm">
                <div className="fieldRow">
                  <label className="field">
                    <span>Execution Mode</span>
                    <select
                      value={mode}
                      onChange={(e) => setMode(e.target.value as "PAPER" | "TESTNET")}
                      disabled={isRunning}
                      className="selectInput"
                    >
                      <option value="PAPER">Paper Trading (Simulated)</option>
                      <option value="TESTNET">Binance Futures Testnet (Live API)</option>
                    </select>
                  </label>

                  <label className="field">
                    <span>Strategy</span>
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      disabled={isRunning}
                      className="selectInput"
                    >
                      <option value="ema_rsi">EMA Crossover + RSI Momentum</option>
                      <option value="bollinger_reversion">Bollinger Bands Mean Reversion</option>
                      <option value="grid">Grid Trading Strategy</option>
                      <option value="dca">DCA Pullback Strategy</option>
                    </select>
                  </label>
                </div>

                <div className="fieldRow">
                  <label className="field">
                    <span>Symbol</span>
                    <select
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                      disabled={isRunning}
                      className="selectInput"
                    >
                      <option value="BTCUSDT">BTCUSDT</option>
                      <option value="ETHUSDT">ETHUSDT</option>
                      <option value="SOLUSDT">SOLUSDT</option>
                      <option value="BNBUSDT">BNBUSDT</option>
                    </select>
                  </label>

                  <label className="field">
                    <span>Candle Timeframe</span>
                    <select
                      value={interval}
                      onChange={(e) => setInterval(e.target.value)}
                      disabled={isRunning}
                      className="selectInput"
                    >
                      <option value="1m">1 Minute</option>
                      <option value="5m">5 Minutes</option>
                      <option value="15m">15 Minutes</option>
                      <option value="1h">1 Hour</option>
                    </select>
                  </label>

                  <label className="field">
                    <span>Poll Rate (Seconds)</span>
                    <input
                      type="number"
                      value={pollInterval}
                      onChange={(e) => setPollInterval(Number(e.target.value))}
                      disabled={isRunning}
                      min="5"
                      max="120"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Live Terminal Log Stream & Trades */}
          <div className="botRightCol">
            {/* Terminal Console */}
            <div className="terminalPanel">
              <div className="terminalHeader">
                <div className="terminalTitle">
                  <Terminal size={14} />
                  <span>Autopilot Decision Stream</span>
                </div>
                <span className="terminalUptime">
                  {data?.last_tick_time ? `Last: ${data.last_tick_time}` : "Ready"}
                </span>
              </div>
              <div className="terminalBody">
                {data?.recent_logs && data.recent_logs.length > 0 ? (
                  data.recent_logs.map((log, i) => (
                    <div key={i} className={`terminalLine ${log.level.toLowerCase()}`}>
                      <span className="logTime">[{log.timestamp}]</span>
                      <span className={`logBadge ${log.level.toLowerCase()}`}>{log.level}</span>
                      <span className="logMessage">{log.message}</span>
                    </div>
                  ))
                ) : (
                  <div className="terminalLine info">
                    <span className="logMessage">Awaiting bot activation...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Executed Trades */}
            <div className="dataPanel" style={{ marginTop: "20px" }}>
              <div className="panelTitle">
                <div>
                  <p className="eyebrow">Execution Journal</p>
                  <h3>Completed Strategy Trades</h3>
                </div>
                <History size={18} className="mutedIcon" />
              </div>

              {!data?.recent_trades || data.recent_trades.length === 0 ? (
                <p className="emptyTableNotice">No trades executed yet by the bot runner.</p>
              ) : (
                <div className="tradeTableContainer smallTable">
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Entry ($)</th>
                        <th>Exit ($)</th>
                        <th>Qty</th>
                        <th>PnL</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_trades.map((t) => (
                        <tr key={t.id}>
                          <td>{t.exit_time}</td>
                          <td>{t.symbol}</td>
                          <td>${t.entry_price.toLocaleString()}</td>
                          <td>${t.exit_price.toLocaleString()}</td>
                          <td>{t.quantity}</td>
                          <td className={t.pnl >= 0 ? "positive" : "negative"}>
                            <strong>{t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}</strong> ({t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct.toFixed(2)}%)
                          </td>
                          <td className="reasonCell">{t.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
