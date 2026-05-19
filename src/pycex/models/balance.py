"""Unified balance model."""

from __future__ import annotations

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
    raw: dict = {}  # noqa: RUF012

    def get(self, asset: str) -> BalanceEntry | None:
        for entry in self.assets:
            if entry.asset.upper() == asset.upper():
                return entry
        return None
