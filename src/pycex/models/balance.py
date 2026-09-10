"""Unified balance model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BalanceEntry(BaseModel):
    """Balance for a single asset."""

    asset: str
    free: float
    locked: float

    @property
    def total(self) -> float:
        return self.free + self.locked


class Balance(BaseModel):
    """Unified account balance."""

    assets: list[BalanceEntry]
    #: The exchange's balance response verbatim. A list when the endpoint returns a
    #: bare array (Binance's `/fapi/v2/balance`, Upbit/Bithumb's `/v1/accounts`) —
    #: wrapping those in a fabricated envelope would make `raw` claim a shape the
    #: endpoint never sent.
    raw: dict[str, Any] | list[Any] = {}  # noqa: RUF012

    def get(self, asset: str) -> BalanceEntry | None:
        for entry in self.assets:
            if entry.asset.upper() == asset.upper():
                return entry
        return None
