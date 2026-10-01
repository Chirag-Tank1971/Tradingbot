"""Order service functions used by the CLI."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .client import BinanceFuturesClient


def place_market_order(
    client: BinanceFuturesClient,
    *,
    symbol: str,
    side: str,
    quantity: str,
) -> dict[str, str]:
    """Place a market order and return display-ready order details."""
    response = client.place_market_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
    )
    return format_order_result(response)


def place_limit_order(
    client: BinanceFuturesClient,
    *,
    symbol: str,
    side: str,
    quantity: str,
    price: str,
) -> dict[str, str]:
    """Place a limit order and return display-ready order details."""
    response = client.place_limit_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
    )
    return format_order_result(response)


def format_order_result(response: dict[str, Any]) -> dict[str, str]:
    """Extract the fields a user needs from a Binance order response."""
    executed_qty = str(response.get("executedQty", "0"))
    cumulative_quote_qty = str(response.get("cumQuote", "0"))

    return {
        "order_id": str(response.get("orderId", "")),
        "status": str(response.get("status", "")),
        "executed_qty": executed_qty,
        "average_price": calculate_average_price(executed_qty, cumulative_quote_qty),
        "client_order_id": str(response.get("clientOrderId", "")),
    }


def calculate_average_price(executed_qty: str, cumulative_quote_qty: str) -> str:
    """Calculate an average execution price from Binance futures response data."""
    try:
        quantity = Decimal(executed_qty)
        quote_quantity = Decimal(cumulative_quote_qty)
    except (InvalidOperation, ValueError):
        return "0"

    if quantity <= 0:
        return "0"

    return format((quote_quantity / quantity).normalize(), "f")

