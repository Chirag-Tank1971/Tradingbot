"""Custom exceptions used by the trading bot."""


class TradingBotError(Exception):
    """Base exception for recoverable trading bot errors."""


class ConfigurationError(TradingBotError):
    """Raised when required configuration is missing or invalid."""


class ValidationError(TradingBotError):
    """Raised when user input fails validation."""


class OrderExecutionError(TradingBotError):
    """Raised when Binance rejects an order or a network error occurs."""

