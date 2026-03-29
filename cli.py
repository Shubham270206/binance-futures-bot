#!/usr/bin/env python3
"""
cli.py — CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
    # Market BUY
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    # Limit SELL
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000

    # Stop-Market BUY (bonus order type)
    python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 90000

    # Verbose logging to console
    python cli.py --symbol ETHUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
"""

from __future__ import annotations

import argparse
import os
import sys

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order
from bot.validators import validate_all


# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

def _env(name: str) -> str:
    """Return env var value or empty string."""
    return os.environ.get(name, "")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot\n"
            "Place MARKET, LIMIT, or STOP_MARKET orders on USDT-M Futures Testnet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Market BUY:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  Limit SELL:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000

  Stop-Market BUY:
    python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 90000

API keys can be passed as flags or set via environment variables:
  export BINANCE_API_KEY=your_key
  export BINANCE_API_SECRET=your_secret
        """,
    )

    # --- Credentials ---
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "--api-key",
        default=_env("BINANCE_API_KEY"),
        help="Binance API key (or set BINANCE_API_KEY env var)",
    )
    creds.add_argument(
        "--api-secret",
        default=_env("BINANCE_API_SECRET"),
        help="Binance API secret (or set BINANCE_API_SECRET env var)",
    )

    # --- Order parameters ---
    order = parser.add_argument_group("Order parameters")
    order.add_argument(
        "--symbol", "-s",
        required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
        help="Order type: MARKET, LIMIT, or STOP_MARKET",
    )
    order.add_argument(
        "--quantity", "-q",
        required=True,
        help="Order quantity (base asset amount, e.g. 0.001 for BTC)",
    )
    order.add_argument(
        "--price", "-p",
        default=None,
        help="Limit price — required for LIMIT orders",
    )
    order.add_argument(
        "--stop-price",
        default=None,
        help="Stop trigger price — required for STOP_MARKET orders",
    )
    order.add_argument(
        "--time-in-force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force for LIMIT orders (default: GTC)",
    )
    order.add_argument(
        "--reduce-only",
        action="store_true",
        default=False,
        help="Mark the order as reduce-only (closes positions only)",
    )

    # --- Logging ---
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        type=str.upper,
        help="Console log verbosity (default: INFO). File always captures DEBUG.",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Set up logging before anything else
    setup_logging(log_level=args.log_level)
    logger = get_logger("cli")

    # --- Validate credentials ---
    if not args.api_key:
        parser.error(
            "API key is required. Use --api-key or set BINANCE_API_KEY."
        )
    if not args.api_secret:
        parser.error(
            "API secret is required. Use --api-secret or set BINANCE_API_SECRET."
        )

    # --- Validate order parameters ---
    try:
        validated = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        print(f"\n\033[91m✗  Validation error: {exc}\033[0m\n")
        sys.exit(2)

    logger.debug("Validated params: %s", {k: str(v) for k, v in validated.items()})

    # --- Build client ---
    client = BinanceFuturesClient(
        api_key=args.api_key,
        api_secret=args.api_secret,
    )

    # --- Place the order ---
    exit_code = place_order(
        client=client,
        symbol=validated["symbol"],
        side=validated["side"],
        order_type=validated["order_type"],
        quantity=validated["quantity"],
        price=validated["price"],
        stop_price=validated["stop_price"],
        time_in_force=args.time_in_force,
        reduce_only=args.reduce_only,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
