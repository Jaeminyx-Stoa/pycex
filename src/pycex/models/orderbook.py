"""Unified order book model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OrderBookEntry(BaseModel):
    """Single price level in the order book."""

    price: float
    amount: float


class OrderBook(BaseModel):
    """Unified order book data."""

    symbol: str
    bids: list[OrderBookEntry]
    asks: list[OrderBookEntry]
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012
