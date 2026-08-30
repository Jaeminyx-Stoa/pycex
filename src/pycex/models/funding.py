"""Unified funding rate model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FundingRate(BaseModel):
    """Perpetual swap funding rate."""

    symbol: str
    rate: float  # per-interval rate as fraction (0.0001 = 1bp)
    interval_hours: int = 8
    next_funding_time: int = 0
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012
