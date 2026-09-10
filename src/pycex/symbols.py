"""Canonical symbol notation: spot ``BASE/QUOTE``, linear perpetual ``BASE/QUOTE:SETTLE``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pycex.exceptions import SymbolNotFoundError

MarketType = Literal["spot", "linear"]

_RE = re.compile(r"^([A-Z0-9]+)/([A-Z0-9]+)(?::([A-Z0-9]+))?$")


@dataclass(frozen=True)
class Symbol:
    base: str
    quote: str
    settle: str | None = None

    @property
    def market_type(self) -> MarketType:
        return "linear" if self.settle else "spot"

    def __str__(self) -> str:
        return f"{self.base}/{self.quote}" + (f":{self.settle}" if self.settle else "")


def parse_symbol(s: str) -> Symbol:
    m = _RE.match(s.upper())
    if not m:
        raise SymbolNotFoundError(f"not a canonical symbol: {s!r} (expected BASE/QUOTE or BASE/QUOTE:SETTLE)")
    return Symbol(m.group(1), m.group(2), m.group(3))


def spot(base: str, quote: str) -> str:
    return f"{base.upper()}/{quote.upper()}"


def linear(base: str, quote: str, settle: str | None = None) -> str:
    return f"{base.upper()}/{quote.upper()}:{(settle or quote).upper()}"
