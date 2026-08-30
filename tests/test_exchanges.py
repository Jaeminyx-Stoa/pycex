"""Tests for exchange initialization and configuration."""

import pytest
from pytest_httpx import HTTPXMock

from pycex import OKX, Binance, Bitget, Bybit
from pycex.constants import BINANCE_BASE, BINANCE_TESTNET, BITGET_BASE, BYBIT_BASE, BYBIT_TESTNET, OKX_BASE
from pycex.exceptions import ExchangeError


class TestBinanceInit:
    def test_default(self) -> None:
        ex = Binance(api_key="k", secret="s")
        assert ex.name == "binance"
        assert ex._http._base_url == BINANCE_BASE

    def test_testnet_deprecated(self) -> None:
        with pytest.deprecated_call():
            ex = Binance(api_key="k", secret="s", testnet=True)
        assert ex.sandbox is True
        assert ex._http._base_url == BINANCE_TESTNET

    def test_sandbox(self) -> None:
        ex = Binance(api_key="k", secret="s", sandbox=True)
        assert ex.sandbox is True
        assert ex._http._base_url == BINANCE_TESTNET

    def test_context_manager(self) -> None:
        with Binance(api_key="k", secret="s") as ex:
            assert ex.name == "binance"


class TestBinanceCancelOrder:
    async def test_cancel_order_400_raises_exchange_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(method="DELETE", status_code=400, json={"code": -2011, "msg": "Unknown order sent."})
        ex = Binance(api_key="k", secret="s")
        with pytest.raises(ExchangeError) as e:
            await ex.cancel_order("1", "BTCUSDT")
        assert e.value.code == -2011
        await ex._http.close()


class TestBybitInit:
    def test_default(self) -> None:
        ex = Bybit(api_key="k", secret="s")
        assert ex.name == "bybit"
        assert ex._http._base_url == BYBIT_BASE

    def test_testnet_deprecated(self) -> None:
        with pytest.deprecated_call():
            ex = Bybit(api_key="k", secret="s", testnet=True)
        assert ex.sandbox is True
        assert ex._http._base_url == BYBIT_TESTNET

    def test_sandbox(self) -> None:
        ex = Bybit(api_key="k", secret="s", sandbox=True)
        assert ex.sandbox is True
        assert ex._http._base_url == BYBIT_TESTNET

    def test_category(self) -> None:
        ex = Bybit(api_key="k", secret="s", category="linear")
        assert ex._category == "linear"

    def test_market_type_linear_maps_to_category(self) -> None:
        ex = Bybit(api_key="k", secret="s", market_type="linear")
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
            candles = await ex.fetch_candles("BTC/USDT")
        assert len(candles) == 1
        assert candles[0].close == 65500.0


class TestOKXInit:
    def test_default(self) -> None:
        ex = OKX(api_key="k", secret="s", passphrase="p")
        assert ex.name == "okx"
        assert ex._http._base_url == OKX_BASE
        assert not ex.sandbox

    def test_demo_deprecated(self) -> None:
        with pytest.deprecated_call():
            ex = OKX(api_key="k", secret="s", passphrase="p", demo=True)
        assert ex.sandbox is True

    def test_sandbox(self) -> None:
        ex = OKX(api_key="k", secret="s", passphrase="p", sandbox=True)
        assert ex.sandbox is True


class TestBitgetInit:
    def test_default(self) -> None:
        ex = Bitget(api_key="k", secret="s", passphrase="p")
        assert ex.name == "bitget"
        assert ex._http._base_url == BITGET_BASE
        assert not ex.sandbox

    def test_demo_deprecated(self) -> None:
        with pytest.deprecated_call():
            ex = Bitget(api_key="k", secret="s", passphrase="p", demo=True)
        assert ex.sandbox is True

    def test_sandbox(self) -> None:
        ex = Bitget(api_key="k", secret="s", passphrase="p", sandbox=True)
        assert ex.sandbox is True
