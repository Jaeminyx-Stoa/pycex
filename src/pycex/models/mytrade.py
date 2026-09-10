"""Unified authenticated (own) trade model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MyTrade(BaseModel):
    """A fill on the caller's own account."""

    id: str
    order_id: str
    symbol: str
    side: str
    price: float
    amount: float
    fee: float = 0.0
    fee_asset: str = ""
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012
