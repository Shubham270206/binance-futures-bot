"""
Binance Futures Testnet client wrapper.

Handles:
  - HMAC-SHA256 request signing
  - Timestamped requests
  - Structured logging of every request / response / error
  - Clean exception hierarchy for callers
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests

from .logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"

# Timeouts (connect, read) in seconds
REQUEST_TIMEOUT = (5, 15)


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message} (HTTP {http_status})")


class BinanceNetworkError(Exception):
    """Raised on connection / timeout failures."""


class BinanceFuturesClient:
    """
    Thin wrapper around Binance USDT-M Futures Testnet REST API.

    Usage:
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        response = client.new_order(symbol="BTCUSDT", side="BUY", ...)
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceFuturesClient initialised. Base URL: %s", self._base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urllib.parse.urlencode(params)
        signature = hmac.new(self._api_secret, query.encode(), hashlib.sha256).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Send an HTTP request, handle signing, logging, and error mapping.
        Returns the parsed JSON response dict.
        """
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            params["signature"] = self._sign(params)

        url = f"{self._base_url}{endpoint}"

        # Log request (mask signature for readability)
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug(
            "REQUEST %s %s | params: %s",
            method.upper(),
            endpoint,
            json.dumps(safe_params),
        )

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                response = self._session.post(url, data=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise BinanceNetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error: %s", exc)
            raise BinanceNetworkError(f"Network error: {exc}") from exc

        # Log raw response
        logger.debug(
            "RESPONSE %s %s | HTTP %d | body: %s",
            method.upper(),
            endpoint,
            response.status_code,
            response.text[:2000],  # cap very large responses in logs
        )

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %d): %s", response.status_code, response.text)
            raise BinanceAPIError(
                code=-1,
                message=f"Non-JSON response: {response.text[:200]}",
                http_status=response.status_code,
            )

        # Binance error payload: {"code": -XXXX, "msg": "..."}
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            err_code = data.get("code", -1)
            err_msg = data.get("msg", "Unknown error")
            logger.error(
                "Binance API error | code: %d | msg: %s | HTTP: %d",
                err_code,
                err_msg,
                response.status_code,
            )
            raise BinanceAPIError(
                code=err_code, message=err_msg, http_status=response.status_code
            )

        if not response.ok:
            logger.error("HTTP error %d: %s", response.status_code, response.text[:500])
            raise BinanceAPIError(
                code=response.status_code,
                message=response.text[:200],
                http_status=response.status_code,
            )

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info (no auth required)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account information."""
        logger.info("Fetching account info")
        return self._request("GET", "/fapi/v2/account")

    def new_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Args:
            symbol:        e.g. 'BTCUSDT'
            side:          'BUY' or 'SELL'
            order_type:    'MARKET', 'LIMIT', or 'STOP_MARKET'
            quantity:      string representation of float quantity
            price:         required for LIMIT orders
            stop_price:    required for STOP_MARKET orders
            time_in_force: 'GTC' (default), 'IOC', 'FOK' — ignored for MARKET
            reduce_only:   whether order should only reduce an existing position
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP_MARKET":
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing %s %s order | symbol=%s | qty=%s | price=%s | stopPrice=%s",
            side,
            order_type,
            symbol,
            quantity,
            price or "N/A",
            stop_price or "N/A",
        )

        result = self._request("POST", "/fapi/v1/order", params=params)
        logger.info(
            "Order placed successfully | orderId=%s | status=%s | executedQty=%s",
            result.get("orderId"),
            result.get("status"),
            result.get("executedQty"),
        )
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order."""
        logger.info("Cancelling order %d for %s", order_id, symbol)
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)
