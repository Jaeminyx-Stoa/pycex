"""Tests for unified Pydantic models."""

from pycex.models import Balance, BalanceEntry, Candle, Order, OrderBook, OrderBookEntry, Ticker, Trade


class TestTicker:
    def test_create(self) -> None:
        t = Ticker(symbol="BTCUSDT", last=50000.0, bid=49999.0, ask=50001.0, high=51000.0, low=49000.0, volume=1234.5)
        assert t.symbol == "BTCUSDT"
        assert t.last == 50000.0
        assert t.bid == 49999.0

    def test_raw(self) -> None:
        t = Ticker(symbol="BTCUSDT", last=50000.0, bid=0, ask=0, high=0, low=0, volume=0, raw={"custom": "data"})
        assert t.raw["custom"] == "data"


class TestOrderBook:
    def test_create(self) -> None:
        ob = OrderBook(
            symbol="BTCUSDT",
            bids=[OrderBookEntry(price=49999.0, amount=1.5)],
            asks=[OrderBookEntry(price=50001.0, amount=2.0)],
        )
        assert ob.symbol == "BTCUSDT"
        assert len(ob.bids) == 1
        assert ob.bids[0].price == 49999.0
        assert ob.asks[0].amount == 2.0


class TestCandle:
    def test_create(self) -> None:
        c = Candle(timestamp=1700000000, open=50000.0, high=51000.0, low=49000.0, close=50500.0, volume=100.0)
        assert c.open == 50000.0
        assert c.close == 50500.0


class TestBalanceEntry:
    def test_total(self) -> None:
        entry = BalanceEntry(asset="BTC", free=1.0, locked=0.5)
        assert entry.total == 1.5


class TestBalance:
    def test_get(self) -> None:
        bal = Balance(
            assets=[
                BalanceEntry(asset="BTC", free=1.0, locked=0.0),
                BalanceEntry(asset="ETH", free=10.0, locked=2.0),
            ]
        )
        btc = bal.get("btc")
        assert btc is not None
        assert btc.free == 1.0

    def test_get_missing(self) -> None:
        bal = Balance(assets=[])
        assert bal.get("XRP") is None


class TestOrder:
    def test_create(self) -> None:
        o = Order(id="123", symbol="BTCUSDT", side="buy", type="limit", amount=0.1, price=50000.0)
        assert o.id == "123"
        assert o.price == 50000.0
        assert o.filled == 0.0


class TestTrade:
    def test_create(self) -> None:
        t = Trade(id="456", symbol="ETHUSDT", side="sell", price=3000.0, amount=5.0, timestamp=1700000000)
        assert t.side == "sell"
        assert t.amount == 5.0
