"""
Order placement logic and response formatting.

Sits between the CLI layer and the raw API client — applies business rules,
formats output for the terminal, and logs human-readable summaries.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Optional

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from .logging_config import get_logger

logger = get_logger("orders")

# ANSI colour codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _fmt(label: str, value: str, colour: str = CYAN) -> str:
    return f"  {BOLD}{label:<20}{RESET}{colour}{value}{RESET}"


def print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal],
    stop_price: Optional[Decimal],
) -> None:
    """Print a clear order request summary before sending."""
    side_colour = GREEN if side == "BUY" else RED
    print(f"\n{BOLD}{'─' * 48}{RESET}")
    print(f"{BOLD}  ORDER REQUEST SUMMARY{RESET}")
    print(f"{BOLD}{'─' * 48}{RESET}")
    print(_fmt("Symbol:", symbol))
    print(_fmt("Side:", side, side_colour))
    print(_fmt("Type:", order_type))
    print(_fmt("Quantity:", str(quantity)))
    if price is not None:
        print(_fmt("Price:", str(price)))
    if stop_price is not None:
        print(_fmt("Stop Price:", str(stop_price)))
    print(f"{BOLD}{'─' * 48}{RESET}\n")


def print_order_response(response: dict) -> None:
    """Print the important fields from a Binance order response."""
    print(f"\n{BOLD}{'─' * 48}{RESET}")
    print(f"{BOLD}  ORDER RESPONSE{RESET}")
    print(f"{BOLD}{'─' * 48}{RESET}")
    print(_fmt("Order ID:", str(response.get("orderId", "N/A"))))
    print(_fmt("Client Order ID:", response.get("clientOrderId", "N/A")))
    print(_fmt("Symbol:", response.get("symbol", "N/A")))
    print(_fmt("Type:", response.get("type", "N/A")))

    side = response.get("side", "N/A")
    print(_fmt("Side:", side, GREEN if side == "BUY" else RED))

    print(_fmt("Status:", response.get("status", "N/A")))
    print(_fmt("Quantity:", response.get("origQty", "N/A")))
    print(_fmt("Executed Qty:", response.get("executedQty", "N/A")))

    avg_price = response.get("avgPrice") or response.get("price", "N/A")
    print(_fmt("Avg / Limit Price:", str(avg_price)))

    time_in_force = response.get("timeInForce", "N/A")
    if time_in_force != "N/A":
        print(_fmt("Time in Force:", time_in_force))

    print(f"{BOLD}{'─' * 48}{RESET}")


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> int:
    """
    Orchestrate order placement:
      1. Print request summary
      2. Call the API client
      3. Print response
      4. Print success / failure message

    Returns exit code: 0 = success, 1 = failure.
    """
    print_request_summary(symbol, side, order_type, quantity, price, stop_price)

    # Convert Decimals to strings for the API
    qty_str = str(quantity)
    price_str = str(price) if price is not None else None
    stop_str = str(stop_price) if stop_price is not None else None

    logger.info(
        "Initiating order | %s %s %s qty=%s price=%s stop=%s",
        side, order_type, symbol, qty_str, price_str or "-", stop_str or "-",
    )

    try:
        response = client.new_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty_str,
            price=price_str,
            stop_price=stop_str,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed — Binance API error: %s", exc)
        print(f"\n{RED}{BOLD}✗  ORDER FAILED{RESET}")
        print(f"  {RED}API Error [{exc.code}]: {exc.message}{RESET}\n")
        return 1
    except BinanceNetworkError as exc:
        logger.error("Order failed — network error: %s", exc)
        print(f"\n{RED}{BOLD}✗  ORDER FAILED — NETWORK ERROR{RESET}")
        print(f"  {RED}{exc}{RESET}\n")
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error placing order")
        print(f"\n{RED}{BOLD}✗  UNEXPECTED ERROR{RESET}")
        print(f"  {RED}{exc}{RESET}\n")
        return 1

    print_order_response(response)

    # Log the full response at DEBUG level for the log file
    logger.debug("Full order response: %s", json.dumps(response))

    print(f"\n{GREEN}{BOLD}✓  ORDER PLACED SUCCESSFULLY{RESET}\n")
    logger.info(
        "Order SUCCESS | orderId=%s | status=%s | executedQty=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
    )
    return 0
