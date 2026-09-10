"""Tests for exception hierarchy."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    NetworkError,
    OrderNotFoundError,
    PyCexError,
    RateLimitError,
)
from pycex.exchanges.binance import _map_error as _binance_map_error
from pycex.exchanges.bitget import _map_error as _bitget_map_error
from pycex.exchanges.bybit import _map_error as _bybit_map_error
from pycex.exchanges.okx import _map_error as _okx_map_error


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


# ── Unified error-mapping contract across the four global adapters ──
#
# Binance, OKX, Bitget, and Bybit each expose a module-level
# ``_map_error(code: str, msg: str) -> PyCexError`` with the same signature
# (Binance's own wire ``code`` is a JSON int, but its ``_error_mapper``
# stringifies before delegating here — see the module docstring in
# src/pycex/exchanges/binance.py). This table asserts every adapter maps at
# least one real, doc-confirmed code per exception type, so the four
# adapters can never silently drift back to a bare/uniform ``ExchangeError``
# for these well-known failure modes. Sources for each code: the module
# docstring of the corresponding exchanges/<name>.py file.

_MapErrorFn = Callable[[str, str], PyCexError]

_UNIFIED_ERROR_MAPPING_CASES: list[tuple[_MapErrorFn, str, type[PyCexError]]] = [
    # Binance
    (_binance_map_error, "-2010", InsufficientBalanceError),
    (_binance_map_error, "-2015", AuthenticationError),
    (_binance_map_error, "-2013", OrderNotFoundError),
    (_binance_map_error, "-1003", RateLimitError),
    # OKX
    (_okx_map_error, "51008", InsufficientBalanceError),
    (_okx_map_error, "50111", AuthenticationError),
    (_okx_map_error, "51603", OrderNotFoundError),
    (_okx_map_error, "50011", RateLimitError),
    # Bitget
    (_bitget_map_error, "40711", InsufficientBalanceError),
    (_bitget_map_error, "40001", AuthenticationError),
    (_bitget_map_error, "40109", OrderNotFoundError),
    (_bitget_map_error, "1001", RateLimitError),
    # Bybit
    (_bybit_map_error, "110007", InsufficientBalanceError),
    (_bybit_map_error, "10003", AuthenticationError),
    (_bybit_map_error, "110001", OrderNotFoundError),
    (_bybit_map_error, "10006", RateLimitError),
]


class TestUnifiedErrorMapping:
    @pytest.mark.parametrize("map_error,code,expected", _UNIFIED_ERROR_MAPPING_CASES)
    def test_maps_known_code_to_expected_exception(
        self, map_error: _MapErrorFn, code: str, expected: type[PyCexError]
    ) -> None:
        err = map_error(code, "x")
        assert isinstance(err, expected)

    @pytest.mark.parametrize("map_error", [_binance_map_error, _okx_map_error, _bitget_map_error, _bybit_map_error])
    def test_unknown_code_falls_back_to_exchange_error(self, map_error: _MapErrorFn) -> None:
        err = map_error("__not_a_real_code__", "x")
        assert isinstance(err, ExchangeError)
        assert not isinstance(err, (InsufficientBalanceError, OrderNotFoundError, RateLimitError))
