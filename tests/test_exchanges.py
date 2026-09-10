"""Tests for exchange initialization and configuration."""

import warnings

import pytest
from pytest_httpx import HTTPXMock

from pycex import OKX, Binance, Bitget, Bybit
from pycex.constants import BINANCE_BASE, BINANCE_TESTNET, BITGET_BASE, BYBIT_BASE, BYBIT_TESTNET, OKX_BASE
from pycex.exceptions import ExchangeError


def _empty_ticker_response(exchange: str) -> dict:
    """Minimal-but-valid ticker payload shape per exchange, for request-shape assertions."""
    if exchange == "binance":
        return {
            "symbol": "BTCUSDT",
            "lastPrice": "1",
            "bidPrice": "1",
            "askPrice": "1",
            "highPrice": "1",
            "lowPrice": "1",
            "volume": "1",
        }
    if exchange == "bybit":
        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "1"}]},
        }
    if exchange == "okx":
        return {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "1"}]}
    if exchange == "bitget":
        return {"code": "00000", "msg": "success", "data": [{"symbol": "BTCUSDT", "lastPr": "1"}]}
    raise ValueError(exchange)


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
            await ex.cancel_order("1", "BTC/USDT")
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
            ticker = await ex.fetch_ticker("BTC/USDT")
        assert ticker.last > 0
        assert ticker.symbol == "BTC/USDT"

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


class TestNoDeprecationOnDefaults:
    """Default construction (no testnet=/demo=) must never warn."""

    def test_default_construction_emits_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Binance(api_key="k", secret="s")


class TestCanonicalSymbolsOnPublicMethods:
    """Every public per-symbol method must send the exchange-native symbol on the
    wire and return the caller's canonical symbol on the parsed model — not just
    fetch_candles. One case per adapter, each exercising the request the adapter
    actually issues and the shape of the model it hands back.
    """

    @pytest.mark.asyncio
    async def test_binance_fetch_ticker_native_request_canonical_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_empty_ticker_response("binance"))
        async with Binance(api_key="k", secret="s") as ex:
            ticker = await ex.fetch_ticker("BTC/USDT")
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("symbol") == "BTCUSDT"
        assert ticker.symbol == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_bybit_fetch_ticker_native_request_canonical_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_empty_ticker_response("bybit"))
        async with Bybit(api_key="k", secret="s") as ex:
            ticker = await ex.fetch_ticker("BTC/USDT")
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("symbol") == "BTCUSDT"
        assert ticker.symbol == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_okx_fetch_ticker_native_request_canonical_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_empty_ticker_response("okx"))
        async with OKX(api_key="k", secret="s", passphrase="p") as ex:
            ticker = await ex.fetch_ticker("BTC/USDT")
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("instId") == "BTC-USDT"
        assert ticker.symbol == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_bitget_fetch_ticker_native_request_canonical_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_empty_ticker_response("bitget"))
        async with Bitget(api_key="k", secret="s", passphrase="p") as ex:
            ticker = await ex.fetch_ticker("BTC/USDT")
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("symbol") == "BTCUSDT"
        assert ticker.symbol == "BTC/USDT"


class TestOKXCandleCursorSemantics:
    """OKX: after=ts -> older than ts, before=ts -> newer than ts; never both at once."""

    @pytest.mark.asyncio
    async def test_since_sends_before_only(self, httpx_mock: HTTPXMock) -> None:
        # An empty `data` array triggers the history-candles fallback (task 9),
        # so a second (also empty) response must be queued for that retry.
        httpx_mock.add_response(json={"code": "0", "msg": "", "data": []})
        httpx_mock.add_response(json={"code": "0", "msg": "", "data": []})
        async with OKX(api_key="k", secret="s", passphrase="p") as ex:
            await ex._fetch_candles_page("BTC-USDT", "1h", since=1_000, until=5_000, limit=100)
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("before") == str(1_000 - 1)
        assert request.url.params.get("after") is None

    @pytest.mark.asyncio
    async def test_until_only_sends_after_only(self, httpx_mock: HTTPXMock) -> None:
        # An empty `data` array triggers the history-candles fallback (task 9),
        # so a second (also empty) response must be queued for that retry.
        httpx_mock.add_response(json={"code": "0", "msg": "", "data": []})
        httpx_mock.add_response(json={"code": "0", "msg": "", "data": []})
        async with OKX(api_key="k", secret="s", passphrase="p") as ex:
            await ex._fetch_candles_page("BTC-USDT", "1h", since=None, until=5_000, limit=100)
        request = httpx_mock.get_requests()[0]
        assert request.url.params.get("after") == str(5_000 + 1)
        assert request.url.params.get("before") is None
