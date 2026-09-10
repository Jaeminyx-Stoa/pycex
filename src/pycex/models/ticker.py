"""Unified ticker model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Ticker(BaseModel):
    """Unified ticker data."""

    symbol: str
    last: float
    bid: float
    ask: float
    high: float
    low: float
    volume: float
    quote_volume: float = 0.0
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012
