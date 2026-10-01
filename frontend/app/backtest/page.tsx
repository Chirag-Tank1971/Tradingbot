"use client";

import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart2,
  CheckCircle2,
  ChevronRight,
  DollarSign,
  Filter,
  Layers,
  LineChart,
  Loader2,
  Percent,
  Play,
  RotateCcw,
  ShieldAlert,
  Sliders,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

type BacktestTrade = {
  id: number;
  entry_time: number;
  exit_time: number;
  side: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_pct: number;
  fees: number;
  exit_reason: string;
};

type EquityPoint = {
  time: number;
  equity: number;
  benchmark: number;
};

type BacktestData = {
  symbol: string;
  interval: string;
  strategy_name: string;
  strategy_description: string;
  initial_capital: number;
  final_equity: number;
  net_profit: number;
  net_profit_pct: number;
  buy_and_hold_return_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  max_drawdown_amount: number;
  equity_curve: EquityPoint[];
  trades: BacktestTrade[];
};

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setInterval] = useState("1h");
  const [limit, setLimit] = useState(300);
  const [strategy, setStrategy] = useState("ema_rsi");
  const [capital, setCapital] = useState(10000);
  const [stopLoss, setStopLoss] = useState<number | "">(2.0);
  const [takeProfit, setTakeProfit] = useState<number | "">(4.0);

  // Strategy specific params
  const [fastEma, setFastEma] = useState(9);
  const [slowEma, setSlowEma] = useState(21);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [rsiOb, setRsiOb] = useState(70);
  const [rsiOs, setRsiOs] = useState(30);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BacktestData | null>(null);
  const [tradeFilter, setTradeFilter] = useState<"ALL" | "WIN" | "LOSS">("ALL");

  const handleRunBacktest = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const payload = {
        symbol,
        interval,
        limit: Number(limit),
        strategy_name: strategy,
        initial_capital: Number(capital),
        stop_loss_pct: stopLoss === "" ? null : Number(stopLoss),
        take_profit_pct: takeProfit === "" ? null : Number(takeProfit),
        strategy_params:
          strategy === "ema_rsi"
            ? {
                fast_period: fastEma,
                slow_period: slowEma,
                rsi_period: rsiPeriod,
                rsi_overbought: rsiOb,
                rsi_oversold: rsiOs,
              }
            : {},
      };

      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.error || json.detail || "Backtest failed");
      }

      setResult(json.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backtest execution error");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredTrades = useMemo(() => {
    if (!result?.trades) return [];
    if (tradeFilter === "WIN") return result.trades.filter((t) => t.pnl > 0);
    if (tradeFilter === "LOSS") return result.trades.filter((t) => t.pnl <= 0);
    return result.trades;
  }, [result, tradeFilter]);

  // Equity curve min/max for SVG rendering
  const equitySvgPoints = useMemo(() => {
    if (!result?.equity_curve || result.equity_curve.length < 2) return null;

    const curve = result.equity_curve;
    const equities = curve.map((c) => c.equity);
    const benchmarks = curve.map((c) => c.benchmark);
    const allVals = [...equities, ...benchmarks];

    const minVal = Math.min(...allVals) * 0.98;
    const maxVal = Math.max(...allVals) * 1.02;
    const range = maxVal - minVal || 1;

    const width = 800;
    const height = 240;

    const equityPoints = curve
      .map((c, i) => {
        const x = (i / (curve.length - 1)) * width;
        const y = height - ((c.equity - minVal) / range) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

    const benchmarkPoints = curve
      .map((c, i) => {
        const x = (i / (curve.length - 1)) * width;
        const y = height - ((c.benchmark - minVal) / range) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

    return { equityPoints, benchmarkPoints, minVal, maxVal, width, height };
  }, [result]);

  return (
    <main className="dashboardShell">
      <section className="dashboardFrame wideFrame">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">Quantitative Engine</p>
            <h1>Strategy Backtesting</h1>
          </div>
          <nav className="topNav" aria-label="Primary navigation">
            <Link href="/">Order Ticket</Link>
            <Link href="/bot">Automated Bot</Link>
            <Link className="active" href="/backtest">
              Backtesting
            </Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </header>

        <div className="backtestLayout">
          {/* Configuration Sidebar */}
          <aside className="backtestConfigPanel">
            <div className="panelTitle">
              <div>
                <p className="eyebrow">Parameters</p>
                <h2>Configuration</h2>
              </div>
              <Sliders size={18} className="mutedIcon" />
            </div>

            <form onSubmit={handleRunBacktest} className="configForm">
              <label className="field">
                <span>Strategy</span>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="selectInput"
                >
                  <option value="ema_rsi">EMA Crossover + RSI Filter</option>
                  <option value="bollinger_reversion">Bollinger Bands Mean Reversion</option>
                  <option value="grid">Grid Trading Strategy</option>
                  <option value="dca">DCA Pullback Strategy</option>
                </select>
              </label>

              <div className="fieldRow">
                <label className="field">
                  <span>Symbol</span>
                  <select
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="selectInput"
                  >
                    <option value="BTCUSDT">BTCUSDT</option>
                    <option value="ETHUSDT">ETHUSDT</option>
                    <option value="SOLUSDT">SOLUSDT</option>
                    <option value="BNBUSDT">BNBUSDT</option>
                  </select>
                </label>

                <label className="field">
                  <span>Interval</span>
                  <select
                    value={interval}
                    onChange={(e) => setInterval(e.target.value)}
                    className="selectInput"
                  >
                    <option value="15m">15m</option>
                    <option value="1h">1h</option>
                    <option value="4h">4h</option>
                    <option value="1d">1d</option>
                  </select>
                </label>
              </div>

              <div className="fieldRow">
                <label className="field">
                  <span>Initial Capital ($)</span>
                  <input
                    type="number"
                    value={capital}
                    onChange={(e) => setCapital(Number(e.target.value))}
                    min="100"
                    step="100"
                  />
                </label>

                <label className="field">
                  <span>Lookback Bars</span>
                  <select
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="selectInput"
                  >
                    <option value={100}>100 bars</option>
                    <option value={200}>200 bars</option>
                    <option value={500}>500 bars</option>
                    <option value={1000}>1000 bars</option>
                  </select>
                </label>
              </div>

              <div className="fieldRow">
                <label className="field">
                  <span>Stop-Loss (%)</span>
                  <input
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value === "" ? "" : Number(e.target.value))}
                    step="0.5"
                    placeholder="None"
                  />
                </label>

                <label className="field">
                  <span>Take-Profit (%)</span>
                  <input
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value === "" ? "" : Number(e.target.value))}
                    step="0.5"
                    placeholder="None"
                  />
                </label>
              </div>

              {strategy === "ema_rsi" && (
                <div className="paramSubGroup">
                  <p className="subGroupLabel">Indicator Settings</p>
                  <div className="fieldRow">
                    <label className="field">
                      <span>Fast EMA</span>
                      <input
                        type="number"
                        value={fastEma}
                        onChange={(e) => setFastEma(Number(e.target.value))}
                        min="2"
                        max="50"
                      />
                    </label>
                    <label className="field">
                      <span>Slow EMA</span>
                      <input
                        type="number"
                        value={slowEma}
                        onChange={(e) => setSlowEma(Number(e.target.value))}
                        min="5"
                        max="200"
                      />
                    </label>
                  </div>
                  <div className="fieldRow">
                    <label className="field">
                      <span>RSI Period</span>
                      <input
                        type="number"
                        value={rsiPeriod}
                        onChange={(e) => setRsiPeriod(Number(e.target.value))}
                        min="2"
                        max="30"
                      />
                    </label>
                    <label className="field">
                      <span>RSI Overbought</span>
                      <input
                        type="number"
                        value={rsiOb}
                        onChange={(e) => setRsiOb(Number(e.target.value))}
                        min="50"
                        max="95"
                      />
                    </label>
                  </div>
                </div>
              )}

              <button
                type="submit"
                className="submitBtn fullWidth"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={16} className="spin" />
                    <span>Simulating Backtest...</span>
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    <span>Run Quantitative Backtest</span>
                  </>
                )}
              </button>
            </form>

            {error && (
              <div className="callout error">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
          </aside>

          {/* Results Analytics Section */}
          <section className="backtestResultsArea">
            {!result && !isLoading && (
              <div className="emptyBacktestPlaceholder">
                <BarChart2 size={48} className="mutedIcon large" />
                <h3>No Simulation Executed</h3>
                <p>
                  Select your strategy parameters on the left and click{" "}
                  <strong>Run Quantitative Backtest</strong> to simulate bar-by-bar
                  execution with realistic fees, slippage, and quant metrics.
                </p>
                <button
                  type="button"
                  onClick={() => handleRunBacktest()}
                  className="quickRunBtn"
                >
                  Run Baseline (BTCUSDT 1h EMA/RSI)
                </button>
              </div>
            )}

            {isLoading && (
              <div className="emptyBacktestPlaceholder">
                <Activity size={48} className="spin" style={{ color: "var(--cyan)" }} />
                <h3>Analyzing Market Data</h3>
                <p>Computing signals, simulated fills, and risk-adjusted metrics...</p>
              </div>
            )}

            {result && !isLoading && (
              <div className="analyticsDashboard">
                {/* Metrics Cards */}
                <div className="metricsGrid">
                  <div className="metricCard">
                    <span className="metricLabel">Strategy Net Return</span>
                    <div className="metricValueRow">
                      <span
                        className={`metricVal ${
                          result.net_profit >= 0 ? "positive" : "negative"
                        }`}
                      >
                        {result.net_profit >= 0 ? "+" : ""}${result.net_profit.toLocaleString()}
                      </span>
                      <span
                        className={`metricBadge ${
                          result.net_profit_pct >= 0 ? "positive" : "negative"
                        }`}
                      >
                        {result.net_profit_pct >= 0 ? "+" : ""}
                        {result.net_profit_pct.toFixed(2)}%
                      </span>
                    </div>
                    <span className="metricSub">
                      Buy & Hold Benchmark:{" "}
                      <strong className={result.buy_and_hold_return_pct >= 0 ? "positive" : "negative"}>
                        {result.buy_and_hold_return_pct >= 0 ? "+" : ""}
                        {result.buy_and_hold_return_pct.toFixed(2)}%
                      </strong>
                    </span>
                  </div>

                  <div className="metricCard">
                    <span className="metricLabel">Sharpe Ratio</span>
                    <div className="metricValueRow">
                      <span
                        className={`metricVal ${
                          result.sharpe_ratio >= 1.0
                            ? "positive"
                            : result.sharpe_ratio >= 0
                            ? "amber"
                            : "negative"
                        }`}
                      >
                        {result.sharpe_ratio.toFixed(2)}
                      </span>
                    </div>
                    <span className="metricSub">
                      Sortino Ratio: <strong>{result.sortino_ratio.toFixed(2)}</strong>
                    </span>
                  </div>

                  <div className="metricCard">
                    <span className="metricLabel">Max Drawdown</span>
                    <div className="metricValueRow">
                      <span className="metricVal negative">
                        -{result.max_drawdown_pct.toFixed(2)}%
                      </span>
                    </div>
                    <span className="metricSub">
                      Peak-to-trough: -${result.max_drawdown_amount.toLocaleString()}
                    </span>
                  </div>

                  <div className="metricCard">
                    <span className="metricLabel">Win Rate & Trades</span>
                    <div className="metricValueRow">
                      <span className="metricVal">
                        {result.win_rate_pct.toFixed(1)}%
                      </span>
                      <span className="metricBadge neutral">
                        {result.total_trades} trades
                      </span>
                    </div>
                    <span className="metricSub">
                      {result.winning_trades}W / {result.losing_trades}L • Profit Factor:{" "}
                      <strong>{result.profit_factor.toFixed(2)}</strong>
                    </span>
                  </div>
                </div>

                {/* Equity Curve SVG Chart */}
                {equitySvgPoints && (
                  <div className="equityChartPanel">
                    <div className="panelTitle">
                      <div>
                        <p className="eyebrow">Performance Curve</p>
                        <h3>Portfolio Growth vs Benchmark</h3>
                      </div>
                      <div className="curveLegend">
                        <span className="legendItem strategyLegend">
                          <span className="legendDot strategyDot" /> Strategy
                        </span>
                        <span className="legendItem benchmarkLegend">
                          <span className="legendDot benchmarkDot" /> Buy & Hold
                        </span>
                      </div>
                    </div>

                    <div className="svgChartContainer">
                      <svg
                        viewBox={`0 0 ${equitySvgPoints.width} ${equitySvgPoints.height}`}
                        className="equitySvg"
                        preserveAspectRatio="none"
                      >
                        <polyline
                          fill="none"
                          stroke="rgba(255, 255, 255, 0.28)"
                          strokeWidth="1.5"
                          strokeDasharray="4 4"
                          points={equitySvgPoints.benchmarkPoints}
                        />
                        <polyline
                          fill="none"
                          stroke="#16a3b8"
                          strokeWidth="2.5"
                          points={equitySvgPoints.equityPoints}
                        />
                      </svg>
                      <div className="svgLabels">
                        <span>${equitySvgPoints.minVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        <span>${equitySvgPoints.maxVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Trade Execution Log */}
                <div className="tradeLogPanel">
                  <div className="tradeLogHeader">
                    <div className="panelTitle">
                      <div>
                        <p className="eyebrow">Audit Trail</p>
                        <h3>Simulated Trade History ({result.trades.length})</h3>
                      </div>
                    </div>

                    <div className="filterChips">
                      <button
                        type="button"
                        className={`chip ${tradeFilter === "ALL" ? "active" : ""}`}
                        onClick={() => setTradeFilter("ALL")}
                      >
                        All ({result.trades.length})
                      </button>
                      <button
                        type="button"
                        className={`chip ${tradeFilter === "WIN" ? "active" : ""}`}
                        onClick={() => setTradeFilter("WIN")}
                      >
                        Winners ({result.winning_trades})
                      </button>
                      <button
                        type="button"
                        className={`chip ${tradeFilter === "LOSS" ? "active" : ""}`}
                        onClick={() => setTradeFilter("LOSS")}
                      >
                        Losers ({result.losing_trades})
                      </button>
                    </div>
                  </div>

                  {filteredTrades.length === 0 ? (
                    <p className="emptyTableNotice">No trades matching filter.</p>
                  ) : (
                    <div className="tradeTableContainer">
                      <table className="dataTable">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Entry Time</th>
                            <th>Exit Time</th>
                            <th>Entry ($)</th>
                            <th>Exit ($)</th>
                            <th>Qty</th>
                            <th>Net PnL</th>
                            <th>Exit Trigger</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredTrades.map((t) => (
                            <tr key={t.id}>
                              <td>{t.id}</td>
                              <td>{new Date(t.entry_time * 1000).toLocaleDateString()} {new Date(t.entry_time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                              <td>{new Date(t.exit_time * 1000).toLocaleDateString()} {new Date(t.exit_time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                              <td>${t.entry_price.toLocaleString()}</td>
                              <td>${t.exit_price.toLocaleString()}</td>
                              <td>{t.quantity}</td>
                              <td className={t.pnl >= 0 ? "positive" : "negative"}>
                                <strong>{t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}</strong> ({t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct.toFixed(2)}%)
                              </td>
                              <td className="reasonCell">{t.exit_reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
