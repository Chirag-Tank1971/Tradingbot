"""Quantitative backtesting engine with bar-by-bar simulation and risk analytics."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from .indicators import calculate_max_drawdown, calculate_sharpe_ratio, calculate_sortino_ratio
from .market_data import Candle, fetch_klines
from .strategies import get_strategy

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Record of a simulated round-trip trade."""

    id: int
    entry_time: int
    exit_time: int
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    fees: float
    exit_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    """Consolidated quantitative backtest metrics and series data."""

    symbol: str
    interval: str
    strategy_name: str
    strategy_description: str
    initial_capital: float
    final_equity: float
    net_profit: float
    net_profit_pct: float
    buy_and_hold_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_amount: float
    equity_curve: list[dict[str, Any]]
    trades: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BacktestEngine:
    """Simulates trading strategies across historical candle bars."""

    def __init__(
        self,
        strategy_name: str,
        strategy_params: dict[str, Any] | None = None,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.0004,  # 0.04% Binance Futures fee
        slippage_pct: float = 0.0005,     # 0.05% slippage
        stop_loss_pct: float | None = 2.0,
        take_profit_pct: float | None = 4.0,
    ) -> None:
        self.strategy = get_strategy(strategy_name, strategy_params)
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def run(
        self,
        candles: list[Candle],
        symbol: str = "BTCUSDT",
        interval: str = "1h",
    ) -> BacktestResult:
        if len(candles) < 25:
            raise ValueError("At least 25 candles required to run backtest")

        cash = self.initial_capital
        in_position = False
        entry_price = 0.0
        entry_time = 0
        quantity = 0.0
        sl_price = 0.0
        tp_price = 0.0

        trades: list[BacktestTrade] = []
        equity_curve: list[dict[str, Any]] = []
        equity_values: list[float] = []
        trade_id = 1

        first_close = candles[0].close

        # Warmup index
        warmup = min(30, len(candles) // 4)

        for i in range(len(candles)):
            c = candles[i]

            # 1. If in position, check Stop-Loss and Take-Profit intra-candle hits
            if in_position:
                exit_occurred = False
                exit_p = 0.0
                reason = ""

                # Stop loss check
                if self.stop_loss_pct is not None and c.low <= sl_price:
                    exit_p = sl_price
                    reason = f"Stop-Loss ({self.stop_loss_pct}%)"
                    exit_occurred = True
                # Take profit check
                elif self.take_profit_pct is not None and c.high >= tp_price:
                    exit_p = tp_price
                    reason = f"Take-Profit ({self.take_profit_pct}%)"
                    exit_occurred = True

                if exit_occurred:
                    exit_p *= (1.0 - self.slippage_pct)
                    gross = quantity * exit_p
                    exit_fee = gross * self.commission_rate
                    net_received = gross - exit_fee
                    trade_pnl = net_received - (quantity * entry_price)
                    trade_pnl_pct = ((exit_p - entry_price) / entry_price) * 100.0

                    cash += net_received
                    trades.append(
                        BacktestTrade(
                            id=trade_id,
                            entry_time=entry_time,
                            exit_time=c.timestamp,
                            side="BUY",
                            entry_price=round(entry_price, 2),
                            exit_price=round(exit_p, 2),
                            quantity=round(quantity, 4),
                            pnl=round(trade_pnl, 2),
                            pnl_pct=round(trade_pnl_pct, 2),
                            fees=round(exit_fee, 2),
                            exit_reason=reason,
                        )
                    )
                    trade_id += 1
                    in_position = False
                    quantity = 0.0

            # 2. Evaluate strategy on bar close (after warmup)
            if i >= warmup:
                sub_history = candles[: i + 1]
                signal, reason = self.strategy.evaluate(sub_history)

                # SELL signal when in position
                if signal == "SELL" and in_position:
                    exit_p = c.close * (1.0 - self.slippage_pct)
                    gross = quantity * exit_p
                    exit_fee = gross * self.commission_rate
                    net_received = gross - exit_fee
                    trade_pnl = net_received - (quantity * entry_price)
                    trade_pnl_pct = ((exit_p - entry_price) / entry_price) * 100.0

                    cash += net_received
                    trades.append(
                        BacktestTrade(
                            id=trade_id,
                            entry_time=entry_time,
                            exit_time=c.timestamp,
                            side="BUY",
                            entry_price=round(entry_price, 2),
                            exit_price=round(exit_p, 2),
                            quantity=round(quantity, 4),
                            pnl=round(trade_pnl, 2),
                            pnl_pct=round(trade_pnl_pct, 2),
                            fees=round(exit_fee, 2),
                            exit_reason=f"Strategy Signal ({reason})",
                        )
                    )
                    trade_id += 1
                    in_position = False
                    quantity = 0.0

                # BUY signal when flat
                elif signal == "BUY" and not in_position and cash > 50.0:
                    entry_p = c.close * (1.0 + self.slippage_pct)
                    available_capital = cash * 0.98  # reserve 2% for fees/buffer
                    qty = available_capital / entry_p
                    entry_fee = (qty * entry_p) * self.commission_rate
                    total_cost = (qty * entry_p) + entry_fee

                    if total_cost <= cash:
                        cash -= total_cost
                        quantity = qty
                        entry_price = entry_p
                        entry_time = c.timestamp
                        in_position = True

                        if self.stop_loss_pct:
                            sl_price = entry_price * (1.0 - (self.stop_loss_pct / 100.0))
                        if self.take_profit_pct:
                            tp_price = entry_price * (1.0 + (self.take_profit_pct / 100.0))

            # 3. Snapshot equity curve at end of bar
            if in_position:
                curr_val = quantity * c.close
                bar_equity = cash + curr_val
            else:
                bar_equity = cash

            benchmark_val = (c.close / first_close) * self.initial_capital
            equity_values.append(bar_equity)
            equity_curve.append(
                {
                    "time": c.timestamp,
                    "equity": round(bar_equity, 2),
                    "benchmark": round(benchmark_val, 2),
                }
            )

        # Close position at the end if still open
        if in_position:
            last_c = candles[-1]
            exit_p = last_c.close
            gross = quantity * exit_p
            exit_fee = gross * self.commission_rate
            net_received = gross - exit_fee
            trade_pnl = net_received - (quantity * entry_price)
            trade_pnl_pct = ((exit_p - entry_price) / entry_price) * 100.0
            cash += net_received
            trades.append(
                BacktestTrade(
                    id=trade_id,
                    entry_time=entry_time,
                    exit_time=last_c.timestamp,
                    side="BUY",
                    entry_price=round(entry_price, 2),
                    exit_price=round(exit_p, 2),
                    quantity=round(quantity, 4),
                    pnl=round(trade_pnl, 2),
                    pnl_pct=round(trade_pnl_pct, 2),
                    fees=round(exit_fee, 2),
                    exit_reason="End of Backtest Period",
                )
            )

        final_equity = cash
        net_profit = final_equity - self.initial_capital
        net_profit_pct = (net_profit / self.initial_capital) * 100.0
        bh_return_pct = ((candles[-1].close - first_close) / first_close) * 100.0

        # Bar-by-bar returns for Sharpe and Sortino
        bar_returns = [
            (equity_values[j] - equity_values[j - 1]) / equity_values[j - 1]
            for j in range(1, len(equity_values))
            if equity_values[j - 1] > 0
        ]

        sharpe = calculate_sharpe_ratio(bar_returns)
        sortino = calculate_sortino_ratio(bar_returns)
        max_dd_amount, max_dd_pct = calculate_max_drawdown(equity_values)

        win_trades = [t for t in trades if t.pnl > 0]
        loss_trades = [t for t in trades if t.pnl <= 0]
        win_rate = (len(win_trades) / len(trades) * 100.0) if trades else 0.0

        gross_profit = sum(t.pnl for t in win_trades)
        gross_loss = abs(sum(t.pnl for t in loss_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        return BacktestResult(
            symbol=symbol,
            interval=interval,
            strategy_name=self.strategy.name,
            strategy_description=self.strategy.get_description(),
            initial_capital=round(self.initial_capital, 2),
            final_equity=round(final_equity, 2),
            net_profit=round(net_profit, 2),
            net_profit_pct=round(net_profit_pct, 2),
            buy_and_hold_return_pct=round(bh_return_pct, 2),
            total_trades=len(trades),
            winning_trades=len(win_trades),
            losing_trades=len(loss_trades),
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_amount=round(max_dd_amount, 2),
            equity_curve=equity_curve,
            trades=[t.to_dict() for t in trades],
        )


def run_backtest_job(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
    strategy_name: str = "ema_rsi",
    strategy_params: dict[str, Any] | None = None,
    initial_capital: float = 10000.0,
    stop_loss_pct: float | None = 2.0,
    take_profit_pct: float | None = 4.0,
) -> dict[str, Any]:
    """Convenience helper to fetch klines and execute backtest."""
    candles = fetch_klines(symbol=symbol, interval=interval, limit=limit)
    engine = BacktestEngine(
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        initial_capital=initial_capital,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
    )
    result = engine.run(candles, symbol=symbol, interval=interval)
    return result.to_dict()
