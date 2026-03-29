"""
Input validation for CLI arguments before any API calls are made.
Raises ValueError with descriptive messages on invalid input.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

# Reasonable sanity bounds — not Binance's exact filters (those are symbol-specific)
MIN_QUANTITY = Decimal("0.000001")
MAX_QUANTITY = Decimal("1_000_000")
MIN_PRICE = Decimal("0.000001")
MAX_PRICE = Decimal("10_000_000")


def validate_symbol(symbol: str) -> str:
    """Normalise and basic-validate a trading symbol like BTCUSDT."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphanumeric (e.g. BTCUSDT)."
        )
    if len(symbol) < 4 or len(symbol) > 20:
        raise ValueError(
            f"Symbol '{symbol}' length is unusual. "
            "Expected something like BTCUSDT (4-20 chars)."
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate order side: BUY or SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type: MARKET, LIMIT, or STOP_MARKET."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str) -> Decimal:
    """Parse and validate order quantity."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    if qty < MIN_QUANTITY:
        raise ValueError(f"Quantity {qty} is below minimum allowed ({MIN_QUANTITY}).")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity {qty} exceeds maximum allowed ({MAX_QUANTITY}).")
    return qty


def validate_price(price: Optional[str]) -> Optional[Decimal]:
    """Parse and validate limit price. Returns None if price is None (market orders)."""
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")
    if p < MIN_PRICE:
        raise ValueError(f"Price {p} is below minimum allowed ({MIN_PRICE}).")
    if p > MAX_PRICE:
        raise ValueError(f"Price {p} exceeds maximum allowed ({MAX_PRICE}).")
    return p


def validate_stop_price(stop_price: Optional[str]) -> Optional[Decimal]:
    """Parse and validate stop price for STOP_MARKET orders."""
    return validate_price(stop_price)


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> dict:
    """
    Run all validations and return a clean params dict.
    Raises ValueError on the first problem found.
    """
    v_symbol = validate_symbol(symbol)
    v_side = validate_side(side)
    v_type = validate_order_type(order_type)
    v_qty = validate_quantity(quantity)

    if v_type == "LIMIT" and price is None:
        raise ValueError("Price is required for LIMIT orders.")
    if v_type == "MARKET" and price is not None:
        raise ValueError("Price must NOT be provided for MARKET orders.")
    if v_type == "STOP_MARKET" and stop_price is None:
        raise ValueError("Stop price (--stop-price) is required for STOP_MARKET orders.")

    v_price = validate_price(price)
    v_stop = validate_stop_price(stop_price)

    return {
        "symbol": v_symbol,
        "side": v_side,
        "order_type": v_type,
        "quantity": v_qty,
        "price": v_price,
        "stop_price": v_stop,
    }
