"""Tests for exception hierarchy."""

from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    NetworkError,
    PyCexError,
    RateLimitError,
)


class TestExceptionHierarchy:
    def test_base(self) -> None:
        assert issubclass(ExchangeError, PyCexError)
        assert issubclass(AuthenticationError, PyCexError)
        assert issubclass(NetworkError, PyCexError)

    def test_exchange_subtypes(self) -> None:
        assert issubclass(RateLimitError, ExchangeError)
        assert issubclass(InsufficientBalanceError, ExchangeError)
        assert issubclass(InvalidOrderError, ExchangeError)

    def test_exchange_error_fields(self) -> None:
        err = ExchangeError("test", code=1001, exchange="binance")
        assert err.code == 1001
        assert err.exchange == "binance"
        assert str(err) == "test"


class TestRaiseCatch:
    def test_catch_as_parent(self) -> None:
        try:
            raise RateLimitError("too fast", exchange="bybit")
        except PyCexError as e:
            assert "too fast" in str(e)
