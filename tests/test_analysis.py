"""Tests for MCP analysis utilities."""

from pycex.mcp.analysis import bollinger_bands, ema, rsi, sma, support_resistance, volatility
from pycex.models.candle import Candle


def _candles(closes: list[float]) -> list[Candle]:
    return [Candle(timestamp=i, open=c, high=c + 1, low=c - 1, close=c, volume=100) for i, c in enumerate(closes)]


class TestSMA:
    def test_basic(self):
        result = sma(_candles([10, 20, 30, 40, 50]), 3)
        assert len(result) == 3
        assert result[0] == 20.0
        assert result[-1] == 40.0

    def test_insufficient_data(self):
        assert sma(_candles([10, 20]), 5) == []


class TestEMA:
    def test_basic(self):
        result = ema(_candles([10, 20, 30, 40, 50]), 3)
        assert len(result) == 3
        assert result[0] == 20.0

    def test_insufficient_data(self):
        assert ema(_candles([10]), 5) == []


class TestRSI:
    def test_all_gains(self):
        assert rsi(_candles([10, 20, 30, 40, 50]), 4) == 100.0

    def test_insufficient_data(self):
        assert rsi(_candles([10, 20]), 14) is None

    def test_range(self):
        val = rsi(_candles([10, 12, 11, 13, 10, 14, 12, 15, 11, 16, 13, 17, 12, 18, 14, 19]), 14)
        assert val is not None
        assert 0 <= val <= 100


class TestVolatility:
    def test_basic(self):
        val = volatility(_candles([100, 102, 98, 101, 99]))
        assert val is not None
        assert val > 0

    def test_insufficient(self):
        assert volatility(_candles([100])) is None


class TestBollingerBands:
    def test_basic(self):
        data = _candles(list(range(100, 125)))
        bb = bollinger_bands(data, 20)
        assert bb is not None
        assert bb["upper"] > bb["middle"] > bb["lower"]
        assert bb["bandwidth"] > 0

    def test_insufficient(self):
        assert bollinger_bands(_candles([10, 20]), 20) is None


class TestSupportResistance:
    def test_basic(self):
        data = _candles([100, 105, 95, 110, 90])
        sr = support_resistance(data)
        assert sr["resistance"] == 111
        assert sr["support"] == 89
        assert sr["range_pct"] > 0
