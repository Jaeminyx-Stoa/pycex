"""Async multi-exchange example — fetch BTC price from all 3 exchanges concurrently."""

import asyncio

from pycex import Binance, Bybit, OKX


async def main() -> None:
    # Open connections to all three exchanges
    async with Binance() as binance, Bybit() as bybit, OKX() as okx:
        # Fetch BTC tickers concurrently
        binance_ticker, bybit_ticker, okx_ticker = await asyncio.gather(
            binance.fetch_ticker("BTCUSDT"),
            bybit.fetch_ticker("BTCUSDT"),
            okx.fetch_ticker("BTC-USDT"),  # OKX uses dash-separated symbols
        )

        print("BTC prices across exchanges:")
        print(f"  Binance : ${binance_ticker.last:,.2f}")
        print(f"  Bybit   : ${bybit_ticker.last:,.2f}")
        print(f"  OKX     : ${okx_ticker.last:,.2f}")
        print()

        # Calculate spread between exchanges
        prices = [binance_ticker.last, bybit_ticker.last, okx_ticker.last]
        spread = max(prices) - min(prices)
        print(f"  Spread  : ${spread:,.2f}")
        print()

        # Fetch ETH tickers concurrently
        eth_binance, eth_bybit, eth_okx = await asyncio.gather(
            binance.fetch_ticker("ETHUSDT"),
            bybit.fetch_ticker("ETHUSDT"),
            okx.fetch_ticker("ETH-USDT"),
        )

        print("ETH prices across exchanges:")
        print(f"  Binance : ${eth_binance.last:,.2f}")
        print(f"  Bybit   : ${eth_bybit.last:,.2f}")
        print(f"  OKX     : ${eth_okx.last:,.2f}")
        print()

        # Fetch order books concurrently
        ob_binance, ob_bybit = await asyncio.gather(
            binance.fetch_order_book("BTCUSDT", limit=5),
            bybit.fetch_order_book("BTCUSDT", limit=5),
        )

        print(f"Binance BTC best bid: ${ob_binance.bids[0].price:,.2f}")
        print(f"Bybit   BTC best bid: ${ob_bybit.bids[0].price:,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
