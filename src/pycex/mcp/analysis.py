"""Analysis utilities for enhanced MCP tools."""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycex.models.candle import Candle


def sma(candles: list[Candle], period: int) -> list[float]:
    closes = [c.close for c in candles]
    if len(closes) < period:
        return []
    return [statistics.mean(closes[i - period : i]) for i in range(period, len(closes) + 1)]


def ema(candles: list[Candle], period: int) -> list[float]:
    closes = [c.close for c in candles]
    if len(closes) < period:
        return []
    k = 2 / (period + 1)
    result = [statistics.mean(closes[:period])]
    for price in closes[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def rsi(candles: list[Candle], period: int = 14) -> float | None:
    closes = [c.close for c in candles]
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-(period):]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def volatility(candles: list[Candle]) -> float | None:
    if len(candles) < 2:
        return None
    closes = [c.close for c in candles]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] != 0]
    if not returns:
        return None
    return statistics.stdev(returns) if len(returns) > 1 else 0.0


def bollinger_bands(candles: list[Candle], period: int = 20, num_std: float = 2.0) -> dict | None:
    closes = [c.close for c in candles]
    if len(closes) < period:
        return None
    recent = closes[-period:]
    middle = statistics.mean(recent)
    std = statistics.stdev(recent)
    return {
        "upper": middle + num_std * std,
        "middle": middle,
        "lower": middle - num_std * std,
        "bandwidth": (num_std * std * 2) / middle * 100,
    }


def support_resistance(candles: list[Candle], lookback: int = 20) -> dict:
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    return {
        "resistance": max(highs),
        "support": min(lows),
        "range_pct": (max(highs) - min(lows)) / min(lows) * 100 if min(lows) > 0 else 0,
    }
