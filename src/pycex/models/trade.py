"""Unified trade model."""

from __future__ import annotations

from pydantic import BaseModel


class Trade(BaseModel):
    """Unified trade data."""

    id: str
    symbol: str
    side: str
    price: float
    amount: float
    timestamp: int = 0
