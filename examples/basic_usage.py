"""Basic pycex usage — Binance ticker and order book (synchronous)."""

from pycex import Binance

# No API key needed for public market data
with Binance() as ex:
    # Fetch current ticker
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(f"BTC/USDT on {ex.name}")
    print(f"  Last price : ${ticker.last:,.2f}")
    print(f"  Bid        : ${ticker.bid:,.2f}")
    print(f"  Ask        : ${ticker.ask:,.2f}")
    print(f"  24h High   : ${ticker.high:,.2f}")
    print(f"  24h Low    : ${ticker.low:,.2f}")
    print(f"  24h Volume : {ticker.volume:,.2f}")
    print()

    # Access the raw Binance API response
    print(f"Raw keys: {list(ticker.raw.keys())[:5]}...")
    print()

    # Fetch order book (top 10 levels)
    ob = ex.fetch_order_book_sync("BTCUSDT", limit=10)
    print(f"Order Book: {ob.symbol}")
    print("  Asks (sell orders):")
    for ask in reversed(ob.asks[:5]):
        print(f"    ${ask.price:>12,.2f}  x  {ask.amount:,.6f} BTC")
    print("  --------")
    print("  Bids (buy orders):")
    for bid in ob.bids[:5]:
        print(f"    ${bid.price:>12,.2f}  x  {bid.amount:,.6f} BTC")

    # Fetch ETH ticker too
    eth = ex.fetch_ticker_sync("ETHUSDT")
    print(f"\nETH/USDT: ${eth.last:,.2f}")
