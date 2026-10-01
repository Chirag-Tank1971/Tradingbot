"""JSON bridge used by the Next.js frontend to place orders."""

from __future__ import annotations

import json
import logging
import sys
from json import JSONDecodeError
from typing import Any

from bot.client import BinanceFuturesClient
from bot.config import load_settings
from bot.exceptions import TradingBotError, ValidationError
from bot.logging_config import configure_logging
from bot.orders import place_limit_order, place_market_order
from bot.validators import validate_order_inputs


logger = logging.getLogger(__name__)


def read_payload() -> dict[str, Any]:
    """Read and decode a JSON request from stdin."""
    raw_payload = sys.stdin.read()
    if not raw_payload.strip():
        raise ValidationError("Request body is required.")

    try:
        payload = json.loads(raw_payload)
    except JSONDecodeError as exc:
        raise ValidationError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    return payload


def submit_order(payload: dict[str, Any]) -> dict[str, str]:
    """Validate and submit an order using the existing bot layers."""
    order = validate_order_inputs(
        symbol=str(payload.get("symbol", "")),
        side=str(payload.get("side", "")),
        order_type=str(payload.get("type", "")),
        quantity=str(payload.get("quantity", "")),
        price=str(payload["price"]) if payload.get("price") not in (None, "") else None,
    )

    settings = load_settings()
    client = BinanceFuturesClient(settings)

    if order["type"] == "MARKET":
        return place_market_order(
            client,
            symbol=str(order["symbol"]),
            side=str(order["side"]),
            quantity=str(order["quantity"]),
        )

    return place_limit_order(
        client,
        symbol=str(order["symbol"]),
        side=str(order["side"]),
        quantity=str(order["quantity"]),
        price=str(order["price"]),
    )


def main() -> int:
    """Run the JSON bridge process."""
    configure_logging()

    try:
        payload = read_payload()
        result = submit_order(payload)
    except TradingBotError as exc:
        logger.error("Frontend order failed: %s", exc)
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1
    except Exception as exc:
        logger.exception("Unexpected frontend order failure")
        print(json.dumps({"success": False, "error": f"Unexpected error: {exc}"}))
        return 1

    print(json.dumps({"success": True, "order": result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

