"use client";

import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowLeftRight,
  BarChart3,
  ClipboardList,
  Loader2,
  RefreshCw,
  Search,
  Wallet,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type DashboardData = {
  symbol: string;
  summary: {
    total_wallet_balance: string;
    available_balance: string;
    total_margin_balance: string;
    unrealized_pnl: string;
    initial_margin: string;
    maintenance_margin: string;
  };
  balances: BalanceRow[];
  positions: PositionRow[];
  open_orders: OrderRow[];
  recent_orders: OrderRow[];
};

type BalanceRow = {
  asset: string;
  wallet_balance: string;
  available_balance: string;
  cross_wallet_balance: string;
};

type PositionRow = {
  symbol: string;
  position_amount: string;
  entry_price: string;
  mark_price: string;
  unrealized_pnl: string;
  leverage: string;
  margin_type: string;
};

type OrderRow = {
  order_id: string;
  symbol: string;
  side: string;
  type: string;
  status: string;
  price: string;
  average_price: string;
  quantity: string;
  executed_quantity: string;
  client_order_id: string;
  updated_at: string;
};

type DashboardResponse = {
  success: boolean;
  error?: string;
  dashboard?: DashboardData;
};

const moneyFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 8,
});

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [activeSymbol, setActiveSymbol] = useState("BTCUSDT");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadDashboard(activeSymbol);
  }, [activeSymbol]);

  const stats = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    return [
      {
        label: "Wallet Balance",
        value: dashboard.summary.total_wallet_balance,
        icon: Wallet,
      },
      {
        label: "Available",
        value: dashboard.summary.available_balance,
        icon: Activity,
      },
      {
        label: "Margin Balance",
        value: dashboard.summary.total_margin_balance,
        icon: BarChart3,
      },
      {
        label: "Unrealized PnL",
        value: dashboard.summary.unrealized_pnl,
        icon: ArrowLeftRight,
      },
      {
        label: "Initial Margin",
        value: dashboard.summary.initial_margin,
        icon: ClipboardList,
      },
      {
        label: "Maintenance",
        value: dashboard.summary.maintenance_margin,
        icon: RefreshCw,
      },
    ];
  }, [dashboard]);

  async function loadDashboard(nextSymbol: string) {
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("/api/dashboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: nextSymbol.trim().toUpperCase() }),
      });
      const data = (await response.json()) as DashboardResponse;

      if (!response.ok || !data.success || !data.dashboard) {
        setError(data.error || "Unable to load dashboard.");
        setDashboard(null);
        return;
      }

      setDashboard(data.dashboard);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Request failed.";
      setError(message);
      setDashboard(null);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSymbolSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveSymbol(symbol.trim().toUpperCase());
  }

  return (
    <main className="dashboardShell">
      <section className="dashboardFrame">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">Binance Futures Testnet</p>
            <h1>Dashboard</h1>
          </div>
          <nav className="topNav" aria-label="Primary navigation">
            <Link href="/">Order Ticket</Link>
            <Link className="active" href="/dashboard">
              Dashboard
            </Link>
          </nav>
        </header>

        <section className="dashboardToolbar" aria-label="Dashboard filters">
          <form className="symbolSearch" onSubmit={handleSymbolSubmit}>
            <Search size={18} aria-hidden="true" />
            <input
              value={symbol}
              onChange={(event) => setSymbol(event.target.value.toUpperCase())}
              autoComplete="off"
              spellCheck={false}
            />
            <button type="submit">Load</button>
          </form>
          <button
            className="refreshButton"
            type="button"
            onClick={() => void loadDashboard(activeSymbol)}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="spin" size={18} aria-hidden="true" />
            ) : (
              <RefreshCw size={18} aria-hidden="true" />
            )}
            Refresh
          </button>
        </section>

        {error ? (
          <div className="dashboardError">
            <AlertCircle size={20} aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        {isLoading && !dashboard ? (
          <div className="dashboardLoading">
            <Loader2 className="spin" size={24} aria-hidden="true" />
            <span>Loading account data</span>
          </div>
        ) : null}

        {dashboard ? (
          <>
            <section className="statGrid" aria-label="Account summary">
              {stats.map((stat) => {
                const Icon = stat.icon;
                return (
                  <article className="metricCard" key={stat.label}>
                    <div className="metricIcon">
                      <Icon size={18} aria-hidden="true" />
                    </div>
                    <span>{stat.label}</span>
                    <strong>{formatNumber(stat.value)}</strong>
                  </article>
                );
              })}
            </section>

            <section className="dashboardGrid">
              <DataPanel title="Balances" count={dashboard.balances.length}>
                <DataTable
                  columns={["Asset", "Wallet", "Available", "Cross Wallet"]}
                  rows={dashboard.balances.map((row) => [
                    row.asset,
                    formatNumber(row.wallet_balance),
                    formatNumber(row.available_balance),
                    formatNumber(row.cross_wallet_balance),
                  ])}
                />
              </DataPanel>

              <DataPanel title="Positions" count={dashboard.positions.length}>
                <DataTable
                  columns={[
                    "Symbol",
                    "Amount",
                    "Entry",
                    "Mark",
                    "PnL",
                    "Lev",
                    "Margin",
                  ]}
                  rows={dashboard.positions.map((row) => [
                    row.symbol,
                    formatNumber(row.position_amount),
                    formatNumber(row.entry_price),
                    formatNumber(row.mark_price),
                    formatNumber(row.unrealized_pnl),
                    row.leverage,
                    row.margin_type || "-",
                  ])}
                />
              </DataPanel>

              <DataPanel title="Open Orders" count={dashboard.open_orders.length}>
                <OrderTable rows={dashboard.open_orders} />
              </DataPanel>

              <DataPanel
                title={`Recent ${dashboard.symbol} Orders`}
                count={dashboard.recent_orders.length}
              >
                <OrderTable rows={dashboard.recent_orders} />
              </DataPanel>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}

function DataPanel({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="dataPanel">
      <div className="panelTitle">
        <h2>{title}</h2>
        <span>{count}</span>
      </div>
      {children}
    </section>
  );
}

function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: string[][];
}) {
  if (rows.length === 0) {
    return <div className="tableEmpty">No records</div>;
  }

  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.join("-")}-${index}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${cell}-${cellIndex}`}>{cell || "-"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrderTable({ rows }: { rows: OrderRow[] }) {
  return (
    <DataTable
      columns={[
        "Order ID",
        "Symbol",
        "Side",
        "Type",
        "Status",
        "Price",
        "Avg",
        "Qty",
        "Filled",
        "Updated",
      ]}
      rows={rows.map((row) => [
        row.order_id,
        row.symbol,
        row.side,
        row.type,
        row.status,
        formatNumber(row.price),
        formatNumber(row.average_price),
        formatNumber(row.quantity),
        formatNumber(row.executed_quantity),
        formatDate(row.updated_at),
      ])}
    />
  );
}

function formatNumber(value: string) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return value || "-";
  }
  return moneyFormatter.format(numericValue);
}

function formatDate(value: string) {
  const timestamp = Number(value);
  if (!Number.isFinite(timestamp) || timestamp <= 0) {
    return "-";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

