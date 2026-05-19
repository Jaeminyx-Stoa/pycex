"""Tests for exchange-specific parsers."""

from pycex.exchanges.binance import _parse_candle, _parse_order, _parse_order_book, _parse_ticker
from pycex.exchanges.bybit import _parse_ticker as bybit_parse_ticker
from pycex.exchanges.okx import _parse_ticker as okx_parse_ticker


class TestBinanceParsers:
    def test_parse_ticker(self) -> None:
        data = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000.00",
            "bidPrice": "49999.00",
            "askPrice": "50001.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
            "volume": "1234.56",
            "quoteVolume": "61728000.00",
            "closeTime": 1700000000000,
        }
        t = _parse_ticker(data)
        assert t.symbol == "BTCUSDT"
        assert t.last == 50000.0
        assert t.volume == 1234.56

    def test_parse_order_book(self) -> None:
        data = {
            "bids": [["49999.00", "1.5"], ["49998.00", "2.0"]],
            "asks": [["50001.00", "1.0"]],
        }
        ob = _parse_order_book("BTCUSDT", data)
        assert ob.symbol == "BTCUSDT"
        assert len(ob.bids) == 2
        assert ob.bids[0].price == 49999.0
        assert ob.asks[0].amount == 1.0

    def test_parse_candle(self) -> None:
        data = [1700000000000, "50000", "51000", "49000", "50500", "100.5", 0, "0", 0, "0", "0", "0"]
        c = _parse_candle(data)
        assert c.open == 50000.0
        assert c.close == 50500.0
        assert c.volume == 100.5

    def test_parse_order(self) -> None:
        data = {
            "orderId": 12345,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "origQty": "0.1",
            "price": "50000.00",
            "executedQty": "0.05",
            "status": "PARTIALLY_FILLED",
            "transactTime": 1700000000000,
        }
        o = _parse_order(data)
        assert o.id == "12345"
        assert o.side == "buy"
        assert o.filled == 0.05


class TestBybitParsers:
    def test_parse_ticker(self) -> None:
        data = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000",
            "bid1Price": "49999",
            "ask1Price": "50001",
            "highPrice24h": "51000",
            "lowPrice24h": "49000",
            "volume24h": "1234.56",
            "turnover24h": "61728000",
        }
        t = bybit_parse_ticker(data)
        assert t.symbol == "BTCUSDT"
        assert t.last == 50000.0


class TestOKXParsers:
    def test_parse_ticker(self) -> None:
        data = {
            "instId": "BTC-USDT",
            "last": "50000",
            "bidPx": "49999",
            "askPx": "50001",
            "high24h": "51000",
            "low24h": "49000",
            "vol24h": "1234.56",
            "volCcy24h": "61728000",
            "ts": "1700000000000",
        }
        t = okx_parse_ticker(data)
        assert t.symbol == "BTC-USDT"
        assert t.last == 50000.0
