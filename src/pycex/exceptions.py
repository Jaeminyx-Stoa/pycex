"""Exception hierarchy for pycex."""

from __future__ import annotations


class PyCexError(Exception):
    """Base exception for all pycex errors."""


class AuthenticationError(PyCexError):
    """Invalid or missing API credentials."""


class ExchangeError(PyCexError):
    """Error returned by the exchange API."""

    def __init__(self, message: str, *, code: str | int | None = None, exchange: str = "") -> None:
        self.code = code
        self.exchange = exchange
        super().__init__(message)


class RateLimitError(ExchangeError):
    """Request was rate-limited by the exchange."""


class InsufficientBalanceError(ExchangeError):
    """Insufficient funds for the requested operation."""


class InvalidOrderError(ExchangeError):
    """Order parameters are invalid."""


class OrderNotFoundError(ExchangeError):
    """Order was not found."""


class NetworkError(PyCexError):
    """Network-level error (timeout, connection refused, etc.)."""


class SymbolNotFoundError(PyCexError):
    """Trading pair/symbol does not exist on the exchange."""
