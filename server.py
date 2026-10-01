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


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health status for deployment checks."""
    return {"status": "ok"}


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

