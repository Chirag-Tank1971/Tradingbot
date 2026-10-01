"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError


DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


@dataclass(frozen=True)
class Settings:
    """Runtime settings required to connect to Binance Futures Testnet."""

    api_key: str
    api_secret: str
    base_url: str = DEFAULT_BASE_URL
    request_timeout: int = 30


def load_settings() -> Settings:
    """Load settings from a local .env file and the process environment."""
    load_dotenv()

    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    base_url = os.getenv("BINANCE_BASE_URL", DEFAULT_BASE_URL).strip()

    missing = []
    if not api_key:
        missing.append("BINANCE_API_KEY")
    if not api_secret:
        missing.append("BINANCE_API_SECRET")

    if missing:
        names = ", ".join(missing)
        raise ConfigurationError(f"Missing required environment variable(s): {names}")

    if not base_url.startswith(("http://", "https://")):
        raise ConfigurationError("BINANCE_BASE_URL must start with http:// or https://")

    return Settings(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url.rstrip("/"),
    )

