"""Unified order model."""

from __future__ import annotations

from pydantic import BaseModel


class Order(BaseModel):
    """Unified order data."""

    id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: float | None = None
    filled: float = 0.0
    status: str = ""
    timestamp: int = 0
    raw: dict = {}  # noqa: RUF012
