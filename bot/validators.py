"""Input validation helpers for order requests."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """Validate and normalize a Binance trading symbol."""
    cleaned = symbol.strip()
    if not cleaned:
        raise ValidationError("Symbol is required.")
    if cleaned != cleaned.upper():
        raise ValidationError("Symbol must be uppercase, for example BTCUSDT.")
    if not cleaned.isalnum():
        raise ValidationError("Symbol must contain only letters and numbers.")
    return cleaned


def validate_side(side: str) -> str:
    """Validate and normalize an order side."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError("Side must be BUY or SELL.")
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Validate and normalize an order type."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError("Order type must be MARKET or LIMIT.")
    return cleaned


def validate_positive_decimal(value: str, field_name: str) -> str:
    """Validate a positive decimal value and return a normalized string."""
    cleaned = str(value).strip()
    try:
        decimal_value = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc

    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be a finite number.")

    if decimal_value <= 0:
        raise ValidationError(f"{field_name} must be greater than 0.")

    return format(decimal_value.normalize(), "f")


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
) -> dict[str, str | None]:
    """Validate CLI order inputs and return normalized values."""
    normalized_type = validate_order_type(order_type)
    normalized_price = None

    if normalized_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        normalized_price = validate_positive_decimal(price, "Price")
    elif price is not None:
        raise ValidationError("Price is only accepted for LIMIT orders.")

    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": normalized_type,
        "quantity": validate_positive_decimal(quantity, "Quantity"),
        "price": normalized_price,
    }
