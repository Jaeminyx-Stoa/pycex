"""Tests for pycex.mcp.server: the shared-factory wiring of compare_prices
and aggregate_balance. get_ticker/get_balance/place_order/cancel_order all
go through _get_exchange -> the same pycex.factory.create_exchange already
covered end-to-end by tests/test_cli.py's factory tests, so they aren't
re-tested here.
"""

from __future__ import annotations

import json

import pytest

from pycex.mcp import server as mcp_server
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.ticker import Ticker


class _StubExchange:
    def __init__(self, symbol_price: float = 100.0, assets: list[BalanceEntry] | None = None) -> None:
        self._symbol_price = symbol_price
        self._assets = assets or []
        self.closed = False

    def fetch_ticker_sync(self, symbol: str) -> Ticker:
        return Ticker(
            symbol=symbol,
            last=self._symbol_price,
            bid=self._symbol_price,
            ask=self._symbol_price,
            high=self._symbol_price,
            low=self._symbol_price,
            volume=1.0,
        )

    def fetch_balance_sync(self) -> Balance:
        return Balance(assets=self._assets)

    def close_sync(self) -> None:
        self.closed = True


# ── compare_prices ──


def test_compare_prices_iterates_configured_exchange_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYCEX_COMPARE_EXCHANGES", "binance,upbit")
    called: list[str] = []

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        called.append(name)
        return _StubExchange(symbol_price=100.0 if name == "binance" else 200.0)

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    result = json.loads(mcp_server.compare_prices("BTC/USDT"))
    assert called == ["binance", "upbit"]
    assert set(result["exchanges"]) == {"binance", "upbit"}
    assert result["arbitrage"]["buy_on"] == "binance"
    assert result["arbitrage"]["sell_on"] == "upbit"


def test_compare_prices_default_exchange_list_excludes_bybit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYCEX_COMPARE_EXCHANGES", raising=False)
    called: list[str] = []

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        called.append(name)
        return _StubExchange()

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    mcp_server.compare_prices("BTC/USDT")
    assert called == ["binance", "okx", "bitget", "upbit", "bithumb", "korbit"]
    assert "bybit" not in called


def test_compare_prices_passes_sandbox_and_market_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYCEX_COMPARE_EXCHANGES", "binance")
    monkeypatch.setenv("PYCEX_SANDBOX", "true")
    monkeypatch.setenv("PYCEX_MARKET_TYPE", "linear")
    seen: dict[str, object] = {}

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        seen.update(kwargs)
        return _StubExchange()

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    mcp_server.compare_prices("BTC/USDT")
    assert seen["sandbox"] is True
    assert seen["market_type"] == "linear"


def test_compare_prices_ignores_deprecated_testnet_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """compare_prices/aggregate_balance are new factory-based code with no
    legacy config to honor — unlike _get_exchange, PYCEX_TESTNET must NOT
    be read as a sandbox fallback here."""
    monkeypatch.setenv("PYCEX_COMPARE_EXCHANGES", "binance")
    monkeypatch.setenv("PYCEX_TESTNET", "true")
    monkeypatch.delenv("PYCEX_SANDBOX", raising=False)
    seen: dict[str, object] = {}

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        seen.update(kwargs)
        return _StubExchange()

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    mcp_server.compare_prices("BTC/USDT")
    assert seen["sandbox"] is False


# ── aggregate_balance ──


def test_aggregate_balance_skips_exchange_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYCEX_COMPARE_EXCHANGES", "binance,upbit")
    monkeypatch.delenv("PYCEX_BINANCE_API_KEY", raising=False)
    monkeypatch.setenv("PYCEX_UPBIT_API_KEY", "k")
    called: list[str] = []

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        called.append(name)
        return _StubExchange(assets=[BalanceEntry(asset="BTC", free=1.0, locked=0.0)])

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    result = json.loads(mcp_server.aggregate_balance())
    assert called == ["upbit"]
    assert "skipped" in result["by_exchange"]["binance"]
    assert result["by_exchange"]["upbit"] == [{"asset": "BTC", "free": 1.0, "locked": 0.0}]
    assert result["aggregated"]["BTC"]["free"] == 1.0


def test_aggregate_balance_no_legacy_env_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """A legacy-style BINANCE_API_KEY (no PYCEX_ prefix) must not be picked
    up — only PYCEX_{NAME}_API_KEY counts."""
    monkeypatch.setenv("PYCEX_COMPARE_EXCHANGES", "binance")
    monkeypatch.setenv("BINANCE_API_KEY", "legacy-key")
    monkeypatch.delenv("PYCEX_BINANCE_API_KEY", raising=False)
    called: list[str] = []

    def fake_create_exchange(name: str, **kwargs: object) -> _StubExchange:
        called.append(name)
        return _StubExchange()

    monkeypatch.setattr(mcp_server, "create_exchange", fake_create_exchange)
    result = json.loads(mcp_server.aggregate_balance())
    assert called == []
    assert "skipped" in result["by_exchange"]["binance"]
