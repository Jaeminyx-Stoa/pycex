"""Record public endpoint responses as test fixtures. Usage: python scripts/record_fixtures.py [exchange]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# (exchange, name, url, params, keep_first_n)
TARGETS = [
    ("upbit", "markets", "https://api.upbit.com/v1/market/all", {"is_details": "true"}, 3),
    ("upbit", "candles_1d", "https://api.upbit.com/v1/candles/days", {"market": "KRW-BTC", "count": 3}, 3),
    ("upbit", "candles_1m", "https://api.upbit.com/v1/candles/minutes/1", {"market": "KRW-BTC", "count": 3}, 3),
    ("upbit", "ticker", "https://api.upbit.com/v1/ticker", {"markets": "KRW-BTC"}, 3),
    ("bithumb", "markets", "https://api.bithumb.com/v1/market/all", {"isDetails": "true"}, 3),
    ("bithumb", "candles_1d", "https://api.bithumb.com/v1/candles/days", {"market": "KRW-BTC", "count": 3}, 3),
    ("bithumb", "ticker", "https://api.bithumb.com/v1/ticker", {"markets": "KRW-BTC"}, 3),
    ("korbit", "markets", "https://api.korbit.co.kr/v2/currencyPairs", {}, 3),
    ("korbit", "candles_1d", "https://api.korbit.co.kr/v2/candles", {"symbol": "btc_krw", "interval": "1D", "limit": 3}, 3),
    ("korbit", "ticker", "https://api.korbit.co.kr/v2/tickers", {"symbol": "btc_krw"}, 3),
    ("binance", "markets_spot", "https://api.binance.com/api/v3/exchangeInfo", {"symbol": "BTCUSDT"}, 0),
    ("binance", "markets_linear", "https://fapi.binance.com/fapi/v1/exchangeInfo", {}, 0),
    ("binance", "candles_linear_1d", "https://fapi.binance.com/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "1d", "limit": 3}, 3),
    ("binance", "funding", "https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": "BTCUSDT"}, 0),
    ("okx", "markets_spot", "https://www.okx.com/api/v5/public/instruments", {"instType": "SPOT", "instId": "BTC-USDT"}, 0),
    ("okx", "markets_swap", "https://www.okx.com/api/v5/public/instruments", {"instType": "SWAP", "instId": "BTC-USDT-SWAP"}, 0),
    ("okx", "candles_swap_1d", "https://www.okx.com/api/v5/market/candles", {"instId": "BTC-USDT-SWAP", "bar": "1D", "limit": 3}, 0),
    ("okx", "funding", "https://www.okx.com/api/v5/public/funding-rate", {"instId": "BTC-USDT-SWAP"}, 0),
    ("bitget", "markets_spot", "https://api.bitget.com/api/v2/spot/public/symbols", {"symbol": "BTCUSDT"}, 0),
    ("bitget", "markets_linear", "https://api.bitget.com/api/v2/mix/market/contracts", {"productType": "USDT-FUTURES", "symbol": "BTCUSDT"}, 0),
    ("bitget", "candles_linear_1d", "https://api.bitget.com/api/v2/mix/market/candles", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "granularity": "1D", "limit": 3}, 0),
    ("bitget", "funding", "https://api.bitget.com/api/v2/mix/market/current-fund-rate", {"symbol": "BTCUSDT", "productType": "USDT-FUTURES"}, 0),
]


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    with httpx.Client(timeout=20) as c:
        for ex, name, url, params, n in TARGETS:
            if only and ex != only:
                continue
            r = c.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if n and isinstance(data, list):
                data = data[:n]
            if n and isinstance(data, dict) and isinstance(data.get("data"), list):
                data["data"] = data["data"][:n]
            p = OUT / ex / f"{name}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print("wrote", p.relative_to(OUT.parent.parent))


if __name__ == "__main__":
    main()
