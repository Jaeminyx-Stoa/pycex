"""Tests for exchange initialization and configuration."""

import pytest
from pytest_httpx import HTTPXMock

from pycex import OKX, Binance, Bitget, Bybit
from pycex.constants import BINANCE_BASE, BINANCE_TESTNET, BITGET_BASE, BYBIT_BASE, BYBIT_TESTNET, OKX_BASE


class TestBinanceInit:
    def test_default(self) -> None:
        ex = Binance(api_key="k", secret="s")
        assert ex.name == "binance"
        assert ex._http._base_url == BINANCE_BASE

    def test_testnet(self) -> None:
        ex = Binance(api_key="k", secret="s", testnet=True)
        assert ex._http._base_url == BINANCE_TESTNET

    def test_context_manager(self) -> None:
        with Binance(api_key="k", secret="s") as ex:
            assert ex.name == "binance"


class TestBybitInit:
    def test_default(self) -> None:
        ex = Bybit(api_key="k", secret="s")
        assert ex.name == "bybit"
        assert ex._http._base_url == BYBIT_BASE

    def test_testnet(self) -> None:
        ex = Bybit(api_key="k", secret="s", testnet=True)
        assert ex._http._base_url == BYBIT_TESTNET

    def test_category(self) -> None:
        ex = Bybit(api_key="k", secret="s", category="linear")
        assert ex._category == "linear"


class TestBybitResponseParsing:
    """Regression: Bybit V5 responses nest data under the JSON key "list" —
    a bulk annotation-fixing script once mangled that string literal into
    "list[Any]" across 8 call sites, which raised KeyError in fetch_ticker
    and silently returned [] everywhere else. These exercise the real key.
    """

    @pytest.mark.asyncio
    async def test_fetch_ticker_reads_list_key(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "category": "spot",
                    "list": [
                        {
                            "symbol": "BTCUSDT",
                            "lastPrice": "65000.5",
                            "bid1Price": "65000.0",
                            "ask1Price": "65001.0",
                            "highPrice24h": "66000.0",
                            "lowPrice24h": "64000.0",
                            "volume24h": "1234.5",
                            "turnover24h": "80000000",
                        }
                    ],
                },
            }
        )
        async with Bybit(api_key="k", secret="s") as ex:
            ticker = await ex.fetch_ticker("BTCUSDT")
        assert ticker.last > 0
        assert ticker.symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_fetch_candles_reads_list_key(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "category": "spot",
                    "symbol": "BTCUSDT",
                    "list": [["1700000000000", "65000", "66000", "64000", "65500", "12.3", "800000"]],
                },
            }
        )
        async with Bybit(api_key="k", secret="s") as ex:
            candles = await ex.fetch_candles("BTCUSDT")
        assert len(candles) == 1
        assert candles[0].close == 65500.0


class TestOKXInit:
    def test_default(self) -> None:
        ex = OKX(api_key="k", secret="s", passphrase="p")
        assert ex.name == "okx"
        assert ex._http._base_url == OKX_BASE
        assert not ex._demo

    def test_demo(self) -> None:
        ex = OKX(api_key="k", secret="s", passphrase="p", demo=True)
        assert ex._demo


class TestBitgetInit:
    def test_default(self) -> None:
        ex = Bitget(api_key="k", secret="s", passphrase="p")
        assert ex.name == "bitget"
        assert ex._http._base_url == BITGET_BASE
        assert not ex._demo

    def test_demo(self) -> None:
        ex = Bitget(api_key="k", secret="s", passphrase="p", demo=True)
        assert ex._demo
