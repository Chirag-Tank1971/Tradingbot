"""Command line interface for placing Binance Futures Testnet orders."""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

from bot.client import BinanceFuturesClient
from bot.config import load_settings
from bot.exceptions import ConfigurationError, OrderExecutionError, TradingBotError
from bot.logging_config import configure_logging
from bot.orders import place_limit_order, place_market_order
from bot.validators import validate_order_inputs


console = Console()
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Place BUY and SELL orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Trading symbol, for example BTCUSDT. Must be uppercase.",
    )
    parser.add_argument(
        "--side",
        required=True,
        help="Order side: BUY or SELL.",
    )
    parser.add_argument(
        "--type",
        required=True,
        dest="order_type",
        help="Order type: MARKET or LIMIT.",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        help="Order quantity. Must be greater than 0.",
    )
    parser.add_argument(
        "--price",
        required=False,
        help="Limit price. Required only for LIMIT orders.",
    )
    return parser


def display_request_summary(order: dict[str, str | None]) -> None:
    """Display the order request before submission."""
    table = Table(title="Trading Request", show_header=False, border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Symbol", str(order["symbol"]))
    table.add_row("Side", str(order["side"]))
    table.add_row("Type", str(order["type"]))
    table.add_row("Qty", str(order["quantity"]))
    if order["price"] is not None:
        table.add_row("Price", str(order["price"]))

    console.print(table)
    console.print("Submitting order...\n", style="bold")


def display_success(result: dict[str, str]) -> None:
    """Display a successful order response."""
    console.print("✅ Order Successful\n", style="bold green")

    table = Table(show_header=False, border_style="green")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Order ID", result["order_id"])
    table.add_row("Status", result["status"])
    table.add_row("Executed Qty", result["executed_qty"])
    table.add_row("Average Price", result["average_price"])
    table.add_row("Client Order ID", result["client_order_id"])
    console.print(table)


def display_failure(message: str) -> None:
    """Display a clean failure message."""
    console.print("❌ Order Failed\n", style="bold red")
    console.print("[bold]Reason:[/bold]")
    console.print(message, style="red")


def submit_order(order: dict[str, str | None]) -> dict[str, str]:
    """Create the Binance client and submit the requested order."""
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


def run(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        order = validate_order_inputs(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
        display_request_summary(order)
        result = submit_order(order)
    except (ConfigurationError, OrderExecutionError, TradingBotError) as exc:
        logger.error("Order failed: %s", exc)
        display_failure(str(exc))
        return 1
    except KeyboardInterrupt:
        logger.warning("Order cancelled by user")
        display_failure("Order cancelled by user.")
        return 130
    except Exception as exc:
        logger.exception("Unexpected error while placing order")
        display_failure(f"Unexpected error: {exc}")
        return 1

    display_success(result)
    return 0


if __name__ == "__main__":
    sys.exit(run())

