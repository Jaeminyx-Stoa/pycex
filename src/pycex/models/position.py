"""Unified derivatives position model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Position(BaseModel):
    """An open (or flat) derivatives position."""

    symbol: str
    side: str  # "long" | "short" | "flat"
    amount: float
    entry_price: float | None = None
    unrealized_pnl: float = 0.0
    leverage: float | None = None
    liquidation_price: float | None = None
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012
