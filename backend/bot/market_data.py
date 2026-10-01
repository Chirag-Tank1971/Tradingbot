"""Market data fetching utilities for Binance Futures candlesticks."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

TESTNET_URL = "https://testnet.binancefuture.com/fapi/v1/klines"
PRODUCTION_URL = "https://fapi.binance.com/fapi/v1/klines"


@dataclass(frozen=True)
class Candle:
    """Standard normalized candlestick representation."""

    timestamp: int  # Open time in seconds (UNIX)
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict[str, Any]:
        """Convert candle to dictionary suitable for JSON serialization."""
        return asdict(self)


def fetch_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
    prefer_testnet: bool = True,
) -> list[Candle]:
    """Fetch candlestick data with automatic fallback between testnet and production endpoints.

    Public market data endpoints do not require API keys.
    """
    symbol = symbol.upper().strip()
    urls = [TESTNET_URL, PRODUCTION_URL] if prefer_testnet else [PRODUCTION_URL, TESTNET_URL]

    last_error: Exception | None = None
    for url in urls:
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(max(limit, 10), 1000),
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                raw_data = response.json()
                candles: list[Candle] = []
                for row in raw_data:
                    candles.append(
                        Candle(
                            timestamp=int(row[0]) // 1000,  # Convert ms to seconds
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=float(row[5]),
                        )
                    )
                return candles
            else:
                logger.warning("Failed klines request to %s: HTTP %s", url, response.status_code)
        except Exception as exc:
            last_error = exc
            logger.warning("Error fetching klines from %s: %s", url, exc)

    if last_error:
        raise RuntimeError(f"Failed to fetch market data for {symbol}: {last_error}")

    raise RuntimeError(f"Could not retrieve klines for symbol {symbol}")
