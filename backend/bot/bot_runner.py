"""Automated strategy execution runner with Paper Trading and Binance Testnet modes."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .client import BinanceFuturesClient
from .config import load_settings
from .exceptions import ConfigurationError
from .market_data import fetch_klines
from .strategies import BaseStrategy, get_strategy

logger = logging.getLogger(__name__)


@dataclass
class BotLogEntry:
    timestamp: str
    level: str
    message: str


@dataclass
class BotTradeEntry:
    id: int
    symbol: str
    mode: str
    side: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    reason: str


class TradingBotRunner:
    """Manages the background execution loop, paper trading, and real testnet orders."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.status: str = "STOPPED"  # STOPPED, RUNNING, ERROR
        self.mode: str = "PAPER"      # PAPER or TESTNET
        self.symbol: str = "BTCUSDT"
        self.interval: str = "1m"
        self.poll_interval: int = 15  # seconds between ticks
        self.strategy_name: str = "ema_rsi"
        self.strategy_params: dict[str, Any] = {}
        self.strategy: BaseStrategy | None = None

        # Paper Trading State
        self.paper_initial_capital: float = 10000.0
        self.paper_cash: float = 10000.0
        self.paper_position_qty: float = 0.0
        self.paper_position_entry: float = 0.0
        self.paper_position_time: str = ""

        # Runtime Stats
        self.last_price: float = 0.0
        self.last_signal: str = "HOLD"
        self.last_signal_reason: str = "Bot initialized"
        self.last_tick_time: str = ""
        self.ticks_count: int = 0
        self.total_realized_pnl: float = 0.0

        self.logs: list[BotLogEntry] = []
        self.trades: list[BotTradeEntry] = []
        self._trade_counter = 1

        self._add_log("INFO", "Trading Bot runner initialized in PAPER mode.")

    def _add_log(self, level: str, message: str) -> None:
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = BotLogEntry(timestamp=now_str, level=level, message=message)
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        logger.info("[BotRunner] %s: %s", level, message)

    def start(self, config: dict[str, Any]) -> dict[str, Any]:
        """Start the automated bot."""
        with self._lock:
            if self.status == "RUNNING":
                return {"success": False, "message": "Bot is already running."}

            self.symbol = config.get("symbol", self.symbol).upper().strip()
            self.interval = config.get("interval", self.interval)
            self.mode = config.get("mode", "PAPER").upper()
            self.strategy_name = config.get("strategy_name", "ema_rsi")
            self.strategy_params = config.get("strategy_params", {})
            self.poll_interval = max(5, int(config.get("poll_interval", 15)))

            try:
                self.strategy = get_strategy(self.strategy_name, self.strategy_params)
            except Exception as exc:
                self._add_log("ERROR", f"Failed to load strategy: {exc}")
                return {"success": False, "message": str(exc)}

            # Check testnet credentials if TESTNET mode selected
            if self.mode == "TESTNET":
                try:
                    load_settings()
                except ConfigurationError as exc:
                    self._add_log("ERROR", f"Cannot run TESTNET mode without API keys: {exc}")
                    return {
                        "success": False,
                        "message": f"Binance credentials missing: {exc}. Please configure .env or use PAPER mode.",
                    }

            self.status = "RUNNING"
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            self._add_log(
                "INFO",
                f"Bot started: {self.strategy.get_description()} on {self.symbol} [{self.mode} mode, poll {self.poll_interval}s]",
            )
            return {"success": True, "status": self.get_status()}

    def stop(self) -> dict[str, Any]:
        """Stop the automated bot."""
        with self._lock:
            if self.status != "RUNNING":
                return {"success": False, "message": "Bot is not running."}

            self._stop_event.set()
            self.status = "STOPPED"
            self._add_log("INFO", "Bot execution stopped by user.")
            return {"success": True, "status": self.get_status()}

    def reset_paper(self) -> dict[str, Any]:
        """Reset simulated paper trading balance and open positions."""
        with self._lock:
            self.paper_cash = self.paper_initial_capital
            self.paper_position_qty = 0.0
            self.paper_position_entry = 0.0
            self.paper_position_time = ""
            self.total_realized_pnl = 0.0
            self.trades.clear()
            self._trade_counter = 1
            self._add_log("INFO", f"Paper trading portfolio reset to ${self.paper_initial_capital:,.2f}")
            return {"success": True, "status": self.get_status()}

    def _run_loop(self) -> None:
        """Background execution worker loop."""
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                self._add_log("ERROR", f"Error during bot tick: {exc}")

            # Sleep in small increments for responsive stop
            for _ in range(self.poll_interval * 2):
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

    def tick(self) -> dict[str, Any]:
        """Execute a single evaluation cycle."""
        with self._lock:
            self.ticks_count += 1
            self.last_tick_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            if not self.strategy:
                self.strategy = get_strategy(self.strategy_name, self.strategy_params)

            # 1. Fetch recent candles
            try:
                candles = fetch_klines(symbol=self.symbol, interval=self.interval, limit=100)
            except Exception as exc:
                self._add_log("WARNING", f"Market data fetch failed: {exc}")
                return {"success": False, "error": str(exc)}

            latest_candle = candles[-1]
            self.last_price = latest_candle.close

            # 2. Evaluate strategy
            signal, reason = self.strategy.evaluate(candles)
            self.last_signal = signal
            self.last_signal_reason = reason

            self._add_log(
                "INFO",
                f"Tick #{self.ticks_count} | {self.symbol} @ ${self.last_price:,.2f} | Signal: {signal} ({reason})",
            )

            # 3. Action Signal
            if self.mode == "PAPER":
                self._execute_paper_signal(signal, reason)
            else:
                self._execute_testnet_signal(signal, reason)

            return {"success": True, "status": self.get_status()}

    def _execute_paper_signal(self, signal: str, reason: str) -> None:
        """Execute paper trade simulation."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # BUY when flat
        if signal == "BUY" and self.paper_position_qty == 0.0:
            if self.paper_cash > 100.0:
                available = self.paper_cash * 0.98  # reserve for fees
                qty = available / self.last_price
                cost = qty * self.last_price
                fee = cost * 0.0004
                total_cost = cost + fee

                if total_cost <= self.paper_cash:
                    self.paper_cash -= total_cost
                    self.paper_position_qty = round(qty, 4)
                    self.paper_position_entry = round(self.last_price, 2)
                    self.paper_position_time = now_str
                    self._add_log(
                        "ACTION",
                        f"[PAPER] BOUGHT {self.paper_position_qty} {self.symbol} at ${self.paper_position_entry:,.2f} (Fee: ${fee:.2f})",
                    )

        # SELL when holding position
        elif signal == "SELL" and self.paper_position_qty > 0.0:
            qty = self.paper_position_qty
            gross = qty * self.last_price
            fee = gross * 0.0004
            net_proceeds = gross - fee
            cost_basis = qty * self.paper_position_entry
            trade_pnl = net_proceeds - cost_basis
            trade_pnl_pct = ((self.last_price - self.paper_position_entry) / self.paper_position_entry) * 100.0

            self.paper_cash += net_proceeds
            self.total_realized_pnl += trade_pnl

            trade = BotTradeEntry(
                id=self._trade_counter,
                symbol=self.symbol,
                mode="PAPER",
                side="BUY->SELL",
                entry_time=self.paper_position_time,
                exit_time=now_str,
                entry_price=self.paper_position_entry,
                exit_price=round(self.last_price, 2),
                quantity=qty,
                pnl=round(trade_pnl, 2),
                pnl_pct=round(trade_pnl_pct, 2),
                reason=reason,
            )
            self.trades.insert(0, trade)
            self._trade_counter += 1

            self._add_log(
                "ACTION",
                f"[PAPER] SOLD {qty} {self.symbol} at ${self.last_price:,.2f} | PnL: ${trade_pnl:+.2f} ({trade_pnl_pct:+.2f}%)",
            )

            # Reset position
            self.paper_position_qty = 0.0
            self.paper_position_entry = 0.0
            self.paper_position_time = ""

    def _execute_testnet_signal(self, signal: str, reason: str) -> None:
        """Execute real order on Binance Testnet."""
        try:
            settings = load_settings()
            client = BinanceFuturesClient(settings)

            if signal == "BUY":
                self._add_log("ACTION", f"[TESTNET] Submitting MARKET BUY order for {self.symbol}...")
                resp = client.place_market_order(symbol=self.symbol, side="BUY", quantity="0.001")
                self._add_log("ACTION", f"[TESTNET] BUY order executed: ID {resp.get('orderId')}")
            elif signal == "SELL":
                self._add_log("ACTION", f"[TESTNET] Submitting MARKET SELL order for {self.symbol}...")
                resp = client.place_market_order(symbol=self.symbol, side="SELL", quantity="0.001")
                self._add_log("ACTION", f"[TESTNET] SELL order executed: ID {resp.get('orderId')}")
        except Exception as exc:
            self._add_log("ERROR", f"[TESTNET] Order placement failed: {exc}")

    def get_status(self) -> dict[str, Any]:
        """Return the current comprehensive state of the bot."""
        # Calculate unrealized PnL
        unrealized_pnl = 0.0
        unrealized_pnl_pct = 0.0
        position_value = 0.0

        if self.paper_position_qty > 0.0 and self.last_price > 0.0:
            position_value = self.paper_position_qty * self.last_price
            cost_basis = self.paper_position_qty * self.paper_position_entry
            unrealized_pnl = position_value - cost_basis
            if cost_basis > 0:
                unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100.0

        total_portfolio_value = self.paper_cash + position_value

        return {
            "status": self.status,
            "mode": self.mode,
            "symbol": self.symbol,
            "interval": self.interval,
            "poll_interval": self.poll_interval,
            "strategy_name": self.strategy_name,
            "strategy_description": self.strategy.get_description() if self.strategy else "",
            "last_price": self.last_price,
            "last_signal": self.last_signal,
            "last_signal_reason": self.last_signal_reason,
            "last_tick_time": self.last_tick_time,
            "ticks_count": self.ticks_count,
            "paper_portfolio": {
                "initial_capital": self.paper_initial_capital,
                "cash": round(self.paper_cash, 2),
                "position_qty": self.paper_position_qty,
                "position_entry": self.paper_position_entry,
                "position_time": self.paper_position_time,
                "position_value": round(position_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                "total_portfolio_value": round(total_portfolio_value, 2),
                "total_realized_pnl": round(self.total_realized_pnl, 2),
            },
            "recent_trades": [asdict(t) for t in self.trades[:15]],
            "recent_logs": [asdict(log) for log in self.logs[-25:]],
        }


# Global singleton instance for the FastAPI application
bot_runner = TradingBotRunner()
