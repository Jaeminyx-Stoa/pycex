"""Unified ticker model."""

from __future__ import annotations

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
    raw: dict = {}  # noqa: RUF012
