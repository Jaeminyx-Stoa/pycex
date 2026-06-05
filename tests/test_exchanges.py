"""Tests for exchange initialization and configuration."""

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
