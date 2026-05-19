"""Bybit and OKX specific usage examples."""

import asyncio

from pycex import Bybit, OKX


def bybit_sync_example() -> None:
    """Bybit synchronous market data."""
    print("=== Bybit (sync) ===")

    with Bybit() as ex:
        # Ticker
        ticker = ex.fetch_ticker_sync("BTCUSDT")
        print(f"BTC/USDT: ${ticker.last:,.2f}")
        print(f"  Bid: ${ticker.bid:,.2f}  Ask: ${ticker.ask:,.2f}")
        print(f"  24h Volume: {ticker.volume:,.2f}")

        # Order book
        ob = ex.fetch_order_book_sync("ETHUSDT", limit=5)
        print(f"\nETH/USDT Order Book:")
        print(f"  Best Ask: ${ob.asks[0].price:,.2f} x {ob.asks[0].amount:,.4f}")
        print(f"  Best Bid: ${ob.bids[0].price:,.2f} x {ob.bids[0].amount:,.4f}")
        print(f"  Spread  : ${ob.asks[0].price - ob.bids[0].price:,.2f}")


def okx_sync_example() -> None:
    """OKX synchronous market data. Note: OKX uses dash-separated symbols."""
    print("\n=== OKX (sync) ===")

    with OKX() as ex:
        # Ticker (OKX uses BTC-USDT format)
        ticker = ex.fetch_ticker_sync("BTC-USDT")
        print(f"BTC-USDT: ${ticker.last:,.2f}")
        print(f"  Bid: ${ticker.bid:,.2f}  Ask: ${ticker.ask:,.2f}")
        print(f"  24h Volume: {ticker.volume:,.2f}")

        # Order book
        ob = ex.fetch_order_book_sync("ETH-USDT", limit=5)
        print(f"\nETH-USDT Order Book:")
        print(f"  Best Ask: ${ob.asks[0].price:,.2f} x {ob.asks[0].amount:,.4f}")
        print(f"  Best Bid: ${ob.bids[0].price:,.2f} x {ob.bids[0].amount:,.4f}")


async def bybit_async_example() -> None:
    """Bybit async market data with candles and trades."""
    print("\n=== Bybit (async) ===")

    async with Bybit() as ex:
        # Fetch candles and trades concurrently
        ticker, candles, trades = await asyncio.gather(
            ex.fetch_ticker("BTCUSDT"),
            ex.fetch_candles("BTCUSDT", "1h", limit=5),
            ex.fetch_trades("BTCUSDT", limit=5),
        )

        print(f"BTC/USDT: ${ticker.last:,.2f}")

        print(f"\nLast {len(candles)} hourly candles:")
        for c in candles:
            print(f"  O={c.open:,.2f} H={c.high:,.2f} L={c.low:,.2f} C={c.close:,.2f} V={c.volume:,.2f}")

        print(f"\nLast {len(trades)} trades:")
        for t in trades:
            print(f"  {t.side:4s} {t.amount:,.6f} @ ${t.price:,.2f}")


async def okx_async_example() -> None:
    """OKX async with demo mode (testnet)."""
    print("\n=== OKX (async, demo mode) ===")

    # OKX demo mode uses the same URL but sets a header flag
    async with OKX(demo=True) as ex:
        ticker = await ex.fetch_ticker("BTC-USDT")
        print(f"BTC-USDT (demo): ${ticker.last:,.2f}")

        ob = await ex.fetch_order_book("BTC-USDT", limit=5)
        print(f"  Best Bid: ${ob.bids[0].price:,.2f}")
        print(f"  Best Ask: ${ob.asks[0].price:,.2f}")

        # Access the raw exchange response
        print(f"\n  Raw response keys: {list(ticker.raw.keys())}")


if __name__ == "__main__":
    # Synchronous examples
    bybit_sync_example()
    okx_sync_example()

    # Async examples
    asyncio.run(bybit_async_example())
    asyncio.run(okx_async_example())
