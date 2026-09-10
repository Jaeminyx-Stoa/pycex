"""Unified derivatives position model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Position(BaseModel):
    """An open (or flat) derivatives position.

    🚨 ``amount`` is the **absolute** size — it is never negative, in any market
    type, on any venue. Direction lives in :attr:`side` and nowhere else.
    Deciding direction from the sign of ``amount`` sends a short's exit the
    wrong way (an *additional* sell), which is exactly how a live position
    failed to close on 2026-09-10. Use :attr:`signed_amount` when a signed
    number is genuinely wanted.
    """

    symbol: str
    #: ``"long"`` | ``"short"`` | ``"flat"`` — the only source of direction.
    side: str
    amount: float = Field(description="Absolute position size; never negative. Direction is in `side`.")
    entry_price: float | None = None
    unrealized_pnl: float = 0.0
    leverage: float | None = None
    liquidation_price: float | None = None
    #: ``"cross"`` | ``"isolated"`` as reported by the venue, or ``None`` when it
    #: did not say. An exit order must carry the mode the position is *actually*
    #: open in; a guessed mode gets the close rejected for a mode mismatch
    #: (measured live, 2026-09-10). pycex therefore reports "unknown" rather
    #: than filling in a default.
    margin_mode: str | None = None
    timestamp: int = 0
    raw: dict[str, Any] = {}  # noqa: RUF012

    @property
    def signed_amount(self) -> float:
        """``amount`` with the direction applied: negative for a short."""
        return -self.amount if self.side == "short" else self.amount
