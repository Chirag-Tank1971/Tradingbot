"""JSON bridge used by the Next.js dashboard."""

from __future__ import annotations

import json
import logging
import sys
from decimal import Decimal, InvalidOperation
from json import JSONDecodeError
from typing import Any

from bot.client import BinanceFuturesClient
from bot.config import load_settings
from bot.exceptions import TradingBotError, ValidationError
from bot.logging_config import configure_logging
from bot.validators import validate_symbol


logger = logging.getLogger(__name__)


def read_payload() -> dict[str, Any]:
    """Read and decode a JSON dashboard request from stdin."""
    raw_payload = sys.stdin.read()
    if not raw_payload.strip():
        return {}

    try:
        payload = json.loads(raw_payload)
    except JSONDecodeError as exc:
        raise ValidationError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    return payload


def load_dashboard(payload: dict[str, Any]) -> dict[str, Any]:
    """Fetch and format dashboard data."""
    symbol = validate_symbol(str(payload.get("symbol") or "BTCUSDT"))
    settings = load_settings()
    client = BinanceFuturesClient(settings)

    account = client.get_account_information()
    balances = client.get_account_balances()
    positions = client.get_position_information()
    open_orders = client.get_open_orders(symbol)
    order_history = client.get_order_history(symbol=symbol, limit=50)

    return {
        "symbol": symbol,
        "summary": format_summary(account),
        "balances": format_balances(balances),
        "positions": format_positions(positions, symbol),
        "open_orders": [format_order(order) for order in open_orders],
        "recent_orders": [format_order(order) for order in reversed(order_history[-20:])],
    }


def format_summary(account: dict[str, Any]) -> dict[str, str]:
    """Format high-level Futures account figures."""
    return {
        "total_wallet_balance": clean_number(account.get("totalWalletBalance")),
        "available_balance": clean_number(account.get("availableBalance")),
        "total_margin_balance": clean_number(account.get("totalMarginBalance")),
        "unrealized_pnl": clean_number(account.get("totalUnrealizedProfit")),
        "initial_margin": clean_number(account.get("totalInitialMargin")),
        "maintenance_margin": clean_number(account.get("totalMaintMargin")),
    }


def format_balances(balances: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Format asset balances, keeping useful non-zero rows."""
    formatted = []
    for balance in balances:
        wallet_balance = clean_number(balance.get("balance"))
        available_balance = clean_number(balance.get("availableBalance"))
        cross_wallet_balance = clean_number(balance.get("crossWalletBalance"))

        balances_are_zero = all(
            is_zero(value)
            for value in (
                wallet_balance,
                available_balance,
                cross_wallet_balance,
            )
        )
        if balances_are_zero:
            continue

        formatted.append(
            {
                "asset": str(balance.get("asset", "")),
                "wallet_balance": wallet_balance,
                "available_balance": available_balance,
                "cross_wallet_balance": cross_wallet_balance,
            }
        )

    return formatted


def format_positions(
    positions: list[dict[str, Any]],
    selected_symbol: str,
) -> list[dict[str, str]]:
    """Format open positions plus the selected symbol row if available."""
    formatted = []
    for position in positions:
        amount = clean_number(position.get("positionAmt"))
        symbol = str(position.get("symbol", ""))

        if is_zero(amount) and symbol != selected_symbol:
            continue

        formatted.append(
            {
                "symbol": symbol,
                "position_amount": amount,
                "entry_price": clean_number(position.get("entryPrice")),
                "mark_price": clean_number(position.get("markPrice")),
                "unrealized_pnl": clean_number(position.get("unRealizedProfit")),
                "leverage": str(position.get("leverage", "")),
                "margin_type": str(position.get("marginType", "")),
            }
        )

    return formatted


def format_order(order: dict[str, Any]) -> dict[str, str]:
    """Format Binance order data for dashboard tables."""
    return {
        "order_id": str(order.get("orderId", "")),
        "symbol": str(order.get("symbol", "")),
        "side": str(order.get("side", "")),
        "type": str(order.get("type", "")),
        "status": str(order.get("status", "")),
        "price": clean_number(order.get("price")),
        "average_price": clean_number(order.get("avgPrice")),
        "quantity": clean_number(order.get("origQty")),
        "executed_quantity": clean_number(order.get("executedQty")),
        "client_order_id": str(order.get("clientOrderId", "")),
        "updated_at": format_timestamp(order.get("updateTime") or order.get("time")),
    }


def clean_number(value: Any) -> str:
    """Return a compact decimal string without changing Binance precision meaning."""
    if value in (None, ""):
        return "0"

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)

    if decimal_value == 0:
        return "0"

    return format(decimal_value.normalize(), "f")


def is_zero(value: str) -> bool:
    """Return whether a formatted decimal string represents zero."""
    try:
        return Decimal(value) == 0
    except (InvalidOperation, ValueError):
        return False


def format_timestamp(value: Any) -> str:
    """Return a millisecond timestamp as a string for frontend formatting."""
    if value in (None, "", 0, "0"):
        return ""
    return str(value)


def main() -> int:
    """Run the dashboard bridge process."""
    configure_logging()

    try:
        payload = read_payload()
        dashboard = load_dashboard(payload)
    except TradingBotError as exc:
        logger.error("Dashboard request failed: %s", exc)
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1
    except Exception as exc:
        logger.exception("Unexpected dashboard request failure")
        print(json.dumps({"success": False, "error": f"Unexpected error: {exc}"}))
        return 1

    print(json.dumps({"success": True, "dashboard": dashboard}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
