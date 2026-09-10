"""Fetch BTC ticker from all six new-in-0.2.0 exchanges concurrently.

No API keys needed — this only touches public endpoints. Bybit (already
supported since 0.1.0) is intentionally omitted; see README's "Supported
Exchanges" table for the full seven-exchange list.
"""

import asyncio

from pycex import create_exchange

# name -> canonical symbol (KRW exchanges quote in KRW, the rest in USDT)
VENUES = {
    "binance": "BTC/USDT",
    "okx": "BTC/USDT",
    "bitget": "BTC/USDT",
    "upbit": "BTC/KRW",
    "bithumb": "BTC/KRW",
    "korbit": "BTC/KRW",
}


async def fetch_one(name: str, symbol: str) -> tuple[str, str, float]:
    async with create_exchange(name) as ex:
        ticker = await ex.fetch_ticker(symbol)
        return name, ticker.symbol, ticker.last


async def main() -> None:
    results = await asyncio.gather(*(fetch_one(name, symbol) for name, symbol in VENUES.items()))
    for name, symbol, last in results:
        print(f"{name:8s} {symbol:8s} {last:,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
