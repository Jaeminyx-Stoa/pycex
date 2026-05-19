"""Unified candle/OHLCV model."""

from __future__ import annotations

from pydantic import BaseModel


class Candle(BaseModel):
    """Unified OHLCV candle data."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
