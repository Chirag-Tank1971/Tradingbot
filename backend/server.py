"""FastAPI backend for the trading bot frontend."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api_dashboard import load_dashboard
from api_order import submit_order
from bot.exceptions import TradingBotError
from bot.logging_config import configure_logging


configure_logging()

app = FastAPI(
    title="Trading Bot API",
    description="Backend API for Binance Futures Testnet order placement.",
    version="1.0.0",
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderRequest(BaseModel):
    symbol: str
    side: str
    type: str
    quantity: str
    price: str | None = None


class DashboardRequest(BaseModel):
    symbol: str = "BTCUSDT"


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    limit: int = 500
    strategy_name: str = "ema_rsi"
    strategy_params: dict[str, Any] = {}
    initial_capital: float = 10000.0
    stop_loss_pct: float | None = 2.0
    take_profit_pct: float | None = 4.0


class BotStartRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    mode: str = "PAPER"
    strategy_name: str = "ema_rsi"
    strategy_params: dict[str, Any] = {}
    poll_interval: int = 15


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health status for deployment checks."""
    return {"status": "ok"}


@app.get("/api/klines")
def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
) -> dict[str, Any]:
    """Fetch candlestick market data for chart display."""
    from bot.market_data import fetch_klines

    try:
        candles = fetch_klines(symbol=symbol, interval=interval, limit=limit)
        return {"success": True, "candles": [c.to_dict() for c in candles]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/backtest")
def backtest(payload: BacktestRequest) -> dict[str, Any]:
    """Execute quantitative backtest across historical candles."""
    from bot.backtester import run_backtest_job

    try:
        result = run_backtest_job(
            symbol=payload.symbol,
            interval=payload.interval,
            limit=payload.limit,
            strategy_name=payload.strategy_name,
            strategy_params=payload.strategy_params,
            initial_capital=payload.initial_capital,
            stop_loss_pct=payload.stop_loss_pct,
            take_profit_pct=payload.take_profit_pct,
        )
        return {"success": True, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/bot/start")
def start_bot(payload: BotStartRequest) -> dict[str, Any]:
    """Start the automated bot runner in PAPER or TESTNET mode."""
    from bot.bot_runner import bot_runner

    res = bot_runner.start(payload.model_dump())
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Failed to start bot"))
    return res


@app.post("/api/bot/stop")
def stop_bot() -> dict[str, Any]:
    """Stop the automated bot runner."""
    from bot.bot_runner import bot_runner

    res = bot_runner.stop()
    return res


@app.get("/api/bot/status")
def bot_status() -> dict[str, Any]:
    """Get active status, portfolio metrics, trades, and logs from the bot runner."""
    from bot.bot_runner import bot_runner

    return {"success": True, "data": bot_runner.get_status()}


@app.post("/api/bot/tick")
def bot_tick() -> dict[str, Any]:
    """Trigger a single tick evaluation immediately."""
    from bot.bot_runner import bot_runner

    return bot_runner.tick()


@app.post("/api/bot/reset")
def bot_reset_paper() -> dict[str, Any]:
    """Reset the simulated paper trading portfolio."""
    from bot.bot_runner import bot_runner

    return bot_runner.reset_paper()


@app.post("/api/orders")
def create_order(payload: OrderRequest) -> dict[str, Any]:
    """Place a Binance Futures Testnet order."""
    try:
        order = submit_order(payload.model_dump())
    except TradingBotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return {"success": True, "order": order}


@app.post("/api/dashboard")
def dashboard(payload: DashboardRequest) -> dict[str, Any]:
    """Return account, balance, position, and order-history data."""
    try:
        dashboard_data = load_dashboard(payload.model_dump())
    except TradingBotError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return {"success": True, "dashboard": dashboard_data}


