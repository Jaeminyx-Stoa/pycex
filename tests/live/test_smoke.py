"""Live smoke tests over the 9 exchange/market-type surfaces.

These hit real public (and, when credentials are present, private) exchange
endpoints. They are excluded from the default test run (see ``addopts`` in
``pyproject.toml``) and only run via ``pytest -m live tests/live``.
"""

from __future__ import annotations

import os
import time

import pytest

from pycex.factory import create_exchange
from pycex.models import Balance

CASES = [
    ("upbit", "spot", "BTC/KRW"),
    ("bithumb", "spot", "BTC/KRW"),
    ("korbit", "spot", "BTC/KRW"),
    ("binance", "spot", "BTC/USDT"),
    ("okx", "spot", "BTC/USDT"),
    ("bitget", "spot", "BTC/USDT"),
    ("binance", "linear", "BTC/USDT:USDT"),
    ("okx", "linear", "BTC/USDT:USDT"),
    ("bitget", "linear", "BTC/USDT:USDT"),
]

# KRW exchanges that reset their daily candle at KST midnight (= 15:00 UTC the
# previous day) instead of UTC midnight. Upbit and the three global venues
# reset at UTC midnight. See tests/fixtures/NOTES.md and docs/api/exchanges.md.
_KST_MIDNIGHT_BOUNDARY = {"bithumb", "korbit"}

# One venue per family for the pagination path (since=/until= over multiple
# pages of BaseExchange.fetch_candles).
PAGINATION_CASES = [
    ("binance", "linear", "BTC/USDT:USDT"),
    ("upbit", "spot", "BTC/KRW"),
    ("korbit", "spot", "BTC/KRW"),
]


@pytest.mark.live
@pytest.mark.parametrize("name,mt,symbol", CASES)
async def test_public_surface(name: str, mt: str, symbol: str) -> None:
    async with create_exchange(name, market_type=mt) as ex:
        markets = await ex.fetch_markets()
        assert any(m.symbol == symbol for m in markets), f"{symbol} missing from {name} markets"

        candles = await ex.fetch_candles(symbol, "1d", limit=5)
        assert 1 <= len(candles) <= 5
        expected_offset = 15 * 3600 * 1000 if name in _KST_MIDNIGHT_BOUNDARY else 0
        assert all(c.timestamp % 86_400_000 == expected_offset for c in candles), (
            f"{name} 1d candles must start at expected day boundary (offset={expected_offset}ms)"
        )

        ticker = await ex.fetch_ticker(symbol)
        assert ticker.last > 0

        ob = await ex.fetch_order_book(symbol)
        assert len(ob.bids) >= 1
        assert len(ob.asks) >= 1

        trades = await ex.fetch_trades(symbol, limit=5)
        assert 1 <= len(trades) <= 5


@pytest.mark.live
@pytest.mark.parametrize("name,mt,symbol", CASES)
async def test_authenticated_smoke(name: str, mt: str, symbol: str) -> None:
    env_key = f"PYCEX_{name.upper()}_API_KEY"
    if not os.environ.get(env_key):
        pytest.skip(f"{env_key} not set")
    async with create_exchange(name, market_type=mt) as ex:
        balance = await ex.fetch_balance()
        assert isinstance(balance, Balance)


@pytest.mark.live
@pytest.mark.parametrize("name,mt,symbol", PAGINATION_CASES)
async def test_candle_pagination(name: str, mt: str, symbol: str) -> None:
    until = int(time.time() * 1000)
    since = until - 10 * 86_400_000
    async with create_exchange(name, market_type=mt) as ex:
        candles = await ex.fetch_candles(symbol, "1d", since=since, until=until)
        assert 9 <= len(candles) <= 11
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps), "candles must be strictly ascending"
        assert len(timestamps) == len(set(timestamps)), "candles must have no duplicate timestamps"
        assert all(b - a > 0 for a, b in zip(timestamps, timestamps[1:])), "candles must be strictly ascending"
