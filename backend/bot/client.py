"""Reusable Binance Futures client wrapper."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from .config import Settings
from .exceptions import OrderExecutionError


logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    """Small wrapper around python-binance for USDT-M Futures Testnet orders."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Client(
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            requests_params={"timeout": settings.request_timeout},
            ping=False,
        )
        self.client.FUTURES_URL = f"{settings.base_url}/fapi"
        self._sync_server_time()

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
    ) -> dict[str, Any]:
        """Place a futures market order."""
        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }
        return self._create_order(payload)

    def place_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
    ) -> dict[str, Any]:
        """Place a futures limit order using GTC time in force."""
        payload = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": price,
        }
        return self._create_order(payload)

    def get_account_information(self) -> dict[str, Any]:
        """Return Futures account information."""
        return self._call_binance("futures_account", self.client.futures_account)

    def get_account_balances(self) -> list[dict[str, Any]]:
        """Return Futures account balances."""
        response = self._call_binance(
            "futures_account_balance",
            self.client.futures_account_balance,
        )
        return list(response)

    def get_position_information(self) -> list[dict[str, Any]]:
        """Return Futures position information."""
        response = self._call_binance(
            "futures_position_information",
            self.client.futures_position_information,
        )
        return list(response)

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Return open Futures orders, optionally filtered by symbol."""
        params = {"symbol": symbol} if symbol else {}
        response = self._call_binance(
            "futures_get_open_orders",
            lambda: self.client.futures_get_open_orders(**params),
        )
        return list(response)

    def get_order_history(
        self,
        *,
        symbol: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return recent Futures orders for a symbol."""
        response = self._call_binance(
            "futures_get_all_orders",
            lambda: self.client.futures_get_all_orders(symbol=symbol, limit=limit),
        )
        return list(response)

    def _create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        logger.info("API Request | futures_create_order | %s", payload)

        try:
            response = self._send_order(payload)
        except BinanceAPIException as exc:
            if exc.code == -1021:
                logger.warning(
                    "Timestamp drift detected; syncing server time and retrying"
                )
                response = self._retry_after_time_sync(payload)
                logger.info("API Response | futures_create_order | %s", response)
                return dict(response)

            logger.error(
                "Binance API error | status=%s | message=%s",
                exc.status_code,
                exc.message,
            )
            raise OrderExecutionError(f"Binance API error: {exc.message}") from exc
        except BinanceRequestException as exc:
            logger.error("Binance request error | message=%s", str(exc))
            raise OrderExecutionError(f"Binance request error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout while placing order", exc_info=True)
            raise OrderExecutionError("Network timeout while contacting Binance.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Network error while placing order", exc_info=True)
            message = f"Network error while contacting Binance: {exc}"
            raise OrderExecutionError(message) from exc

        logger.info("API Response | futures_create_order | %s", response)
        return dict(response)

    def _call_binance(self, operation: str, callback: Any) -> Any:
        logger.info("API Request | %s", operation)

        try:
            response = callback()
        except BinanceAPIException as exc:
            if exc.code == -1021:
                logger.warning("Timestamp drift detected for %s; retrying", operation)
                self._sync_server_time()
                response = self._retry_binance_call(operation, callback)
                logger.info("API Response | %s | %s", operation, response)
                return response

            logger.error(
                "Binance API error | operation=%s | status=%s | message=%s",
                operation,
                exc.status_code,
                exc.message,
            )
            raise OrderExecutionError(f"Binance API error: {exc.message}") from exc
        except BinanceRequestException as exc:
            logger.error(
                "Binance request error | operation=%s | message=%s",
                operation,
                str(exc),
            )
            raise OrderExecutionError(f"Binance request error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout | operation=%s", operation, exc_info=True)
            raise OrderExecutionError("Network timeout while contacting Binance.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Network error | operation=%s", operation, exc_info=True)
            message = f"Network error while contacting Binance: {exc}"
            raise OrderExecutionError(message) from exc

        logger.info("API Response | %s | %s", operation, response)
        return response

    def _retry_binance_call(self, operation: str, callback: Any) -> Any:
        try:
            return callback()
        except BinanceAPIException as exc:
            logger.error(
                "Binance API error after timestamp retry | operation=%s | "
                "status=%s | message=%s",
                operation,
                exc.status_code,
                exc.message,
            )
            raise OrderExecutionError(f"Binance API error: {exc.message}") from exc
        except BinanceRequestException as exc:
            logger.error(
                "Binance request error after timestamp retry | operation=%s | "
                "message=%s",
                operation,
                str(exc),
            )
            raise OrderExecutionError(f"Binance request error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error(
                "Network timeout after timestamp retry | operation=%s",
                operation,
                exc_info=True,
            )
            raise OrderExecutionError("Network timeout while contacting Binance.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(
                "Network error after timestamp retry | operation=%s",
                operation,
                exc_info=True,
            )
            message = f"Network error while contacting Binance: {exc}"
            raise OrderExecutionError(message) from exc

    def _send_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.futures_create_order(**payload)

    def _retry_after_time_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._sync_server_time()

        try:
            return self._send_order(payload)
        except BinanceAPIException as exc:
            logger.error(
                "Binance API error after timestamp retry | status=%s | message=%s",
                exc.status_code,
                exc.message,
            )
            raise OrderExecutionError(f"Binance API error: {exc.message}") from exc
        except BinanceRequestException as exc:
            logger.error(
                "Binance request error after timestamp retry | message=%s",
                str(exc),
            )
            raise OrderExecutionError(f"Binance request error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout after timestamp retry", exc_info=True)
            raise OrderExecutionError("Network timeout while contacting Binance.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Network error after timestamp retry", exc_info=True)
            message = f"Network error while contacting Binance: {exc}"
            raise OrderExecutionError(message) from exc

    def _sync_server_time(self) -> None:
        try:
            server_time = int(self.client.futures_time()["serverTime"])
        except BinanceAPIException as exc:
            logger.error(
                "Unable to fetch Binance server time | status=%s | message=%s",
                exc.status_code,
                exc.message,
            )
            raise OrderExecutionError(f"Binance API error: {exc.message}") from exc
        except BinanceRequestException as exc:
            logger.error("Unable to fetch Binance server time | message=%s", str(exc))
            raise OrderExecutionError(f"Binance request error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error(
                "Network timeout while fetching Binance server time",
                exc_info=True,
            )
            raise OrderExecutionError("Network timeout while contacting Binance.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Network error while fetching Binance server time", exc_info=True)
            message = f"Network error while contacting Binance: {exc}"
            raise OrderExecutionError(message) from exc

        local_time = int(time.time() * 1000)
        self.client.timestamp_offset = server_time - local_time
        logger.info(
            "Binance server time offset set to %sms",
            self.client.timestamp_offset,
        )
