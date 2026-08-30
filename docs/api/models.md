# Models

All API responses are parsed into typed Pydantic models. Every model that
wraps an exchange response includes a `.raw` field with the original data.
Every model's `symbol` field is the canonical `BASE/QUOTE` symbol you passed
in (e.g. `BTC/USDT`), not the exchange's native notation.

## Ticker

Current price and 24-hour statistics for a trading pair.

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    print(f"Symbol      : {ticker.symbol}")
    print(f"Last price  : {ticker.last}")
    print(f"Bid         : {ticker.bid}")
    print(f"Ask         : {ticker.ask}")
    print(f"24h High    : {ticker.high}")
    print(f"24h Low     : {ticker.low}")
    print(f"24h Volume  : {ticker.volume}")
    print(f"Quote Volume: {ticker.quote_volume}")
    print(f"Timestamp   : {ticker.timestamp}")
```

### Ticker Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Canonical trading pair (e.g., `BTC/USDT`) |
| `last` | `float` | Last traded price |
| `bid` | `float` | Best bid price |
| `ask` | `float` | Best ask price |
| `high` | `float` | 24-hour high |
| `low` | `float` | 24-hour low |
| `volume` | `float` | 24-hour base volume |
| `quote_volume` | `float` | 24-hour quote volume |
| `timestamp` | `int` | Unix timestamp (ms) |
| `raw` | `dict` | Original exchange response |

### Ticker Raw Data

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    # Access Binance-specific fields via .raw
    print(ticker.raw["weightedAvgPrice"])
    print(ticker.raw["priceChangePercent"])
```

## OrderBook

Bid and ask price levels for a trading pair.

```python
from pycex import Binance

with Binance() as ex:
    ob = ex.fetch_order_book_sync("ETH/USDT", limit=10)
    print(f"Symbol: {ob.symbol}")

    print("Top 5 asks:")
    for ask in ob.asks[:5]:
        print(f"  ${ask.price:,.2f} x {ask.amount:,.4f}")

    print("Top 5 bids:")
    for bid in ob.bids[:5]:
        print(f"  ${bid.price:,.2f} x {bid.amount:,.4f}")
```

### OrderBook Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Canonical trading pair |
| `bids` | `list[OrderBookEntry]` | Buy orders (highest first) |
| `asks` | `list[OrderBookEntry]` | Sell orders (lowest first) |
| `timestamp` | `int` | Unix timestamp (ms) |
| `raw` | `dict` | Original exchange response |

### OrderBookEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `price` | `float` | Price level |
| `amount` | `float` | Quantity at this price |

### OrderBook Spread Calculation

```python
from pycex import Binance

with Binance() as ex:
    ob = ex.fetch_order_book_sync("BTC/USDT", limit=5)
    spread = ob.asks[0].price - ob.bids[0].price
    spread_pct = spread / ob.bids[0].price * 100
    print(f"Spread: ${spread:,.2f} ({spread_pct:.4f}%)")
```

## Balance

Account balance across all assets.

```python
from pycex import Binance

with Binance(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()

    # Iterate all assets with non-zero balance
    for asset in balance.assets:
        print(f"{asset.asset}: free={asset.free}, locked={asset.locked}, total={asset.total}")

    # Look up a specific asset
    btc = balance.get("BTC")
    if btc:
        print(f"BTC free: {btc.free}")
        print(f"BTC locked: {btc.locked}")
        print(f"BTC total: {btc.total}")
```

### Balance Fields

| Field | Type | Description |
|-------|------|-------------|
| `assets` | `list[BalanceEntry]` | Non-zero asset balances |
| `raw` | `dict` | Original exchange response |

### Balance Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get(asset)` | `BalanceEntry \| None` | Look up a specific asset by name |

### BalanceEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `asset` | `str` | Asset symbol (e.g., `BTC`, `USDT`) |
| `free` | `float` | Available balance |
| `locked` | `float` | Locked in open orders |
| `total` | `float` | Property: `free + locked` |

### Balance Example with Multiple Exchanges

```python
from pycex import Binance, Bybit

with Binance(api_key="B_KEY", secret="B_SECRET") as binance:
    b_bal = binance.fetch_balance_sync()
    b_usdt = b_bal.get("USDT")

with Bybit(api_key="BY_KEY", secret="BY_SECRET") as bybit:
    by_bal = bybit.fetch_balance_sync()
    by_usdt = by_bal.get("USDT")

print(f"Binance USDT: {b_usdt.free if b_usdt else 0}")
print(f"Bybit   USDT: {by_usdt.free if by_usdt else 0}")
```

## Order

Represents a placed, filled, or canceled order.

```python
from pycex import Binance

with Binance(api_key="KEY", secret="SECRET", sandbox=True) as ex:
    # Place a limit buy order
    order = ex.create_order_sync("BTC/USDT", "buy", "limit", amount=0.001, price=50000.0)
    print(f"Order ID : {order.id}")
    print(f"Symbol   : {order.symbol}")
    print(f"Side     : {order.side}")
    print(f"Type     : {order.type}")
    print(f"Amount   : {order.amount}")
    print(f"Price    : {order.price}")
    print(f"Filled   : {order.filled}")
    print(f"Status   : {order.status}")

    # Cancel it
    canceled = ex.cancel_order_sync(order.id, "BTC/USDT")
    print(f"Canceled : {canceled.id}")
```

### Order Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Exchange order ID |
| `symbol` | `str` | Canonical trading pair |
| `side` | `str` | `"buy"` or `"sell"` |
| `type` | `str` | `"limit"` or `"market"` |
| `amount` | `float` | Order quantity |
| `price` | `float \| None` | Limit price (`None` for market) |
| `filled` | `float` | Amount filled so far |
| `status` | `str` | Order status |
| `timestamp` | `int` | Unix timestamp (ms) |
| `raw` | `dict` | Original exchange response |

### Market Order Example

```python
from pycex import Binance

with Binance(api_key="KEY", secret="SECRET", sandbox=True) as ex:
    # Market buy (no price needed)
    order = ex.create_order_sync("BTC/USDT", "buy", "market", amount=0.001)
    print(f"Market buy: {order.id}, filled={order.filled}")
```

## Candle

OHLCV candlestick data.

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        candles = await ex.fetch_candles("BTC/USDT", "1h", limit=5)
        for c in candles:
            print(f"  O={c.open:,.2f} H={c.high:,.2f} L={c.low:,.2f} C={c.close:,.2f} V={c.volume:,.2f}")

asyncio.run(main())
```

### Candle Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `int` | Candle open time (Unix ms) |
| `open` | `float` | Open price |
| `high` | `float` | High price |
| `low` | `float` | Low price |
| `close` | `float` | Close price |
| `volume` | `float` | Trading volume |

### Candle Analysis Example

```python
import asyncio
from pycex import Bybit

async def main():
    async with Bybit() as ex:
        candles = await ex.fetch_candles("BTC/USDT", "1d", limit=30)

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        print(f"30-day high  : ${max(highs):,.2f}")
        print(f"30-day low   : ${min(lows):,.2f}")
        print(f"Avg close    : ${sum(closes) / len(closes):,.2f}")

asyncio.run(main())
```

## Trade

A single executed trade from the public trade feed.

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        trades = await ex.fetch_trades("BTC/USDT", limit=10)
        for t in trades:
            print(f"  {t.side:4s} {t.amount:,.6f} BTC @ ${t.price:,.2f}")

asyncio.run(main())
```

### Trade Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Trade ID |
| `symbol` | `str` | Canonical trading pair |
| `side` | `str` | `"buy"` or `"sell"` |
| `price` | `float` | Execution price |
| `amount` | `float` | Execution quantity |
| `timestamp` | `int` | Unix timestamp (ms) |

### Trade Volume Analysis

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        trades = await ex.fetch_trades("BTC/USDT", limit=100)

        buy_vol = sum(t.amount for t in trades if t.side == "buy")
        sell_vol = sum(t.amount for t in trades if t.side == "sell")

        print(f"Buy  volume: {buy_vol:,.6f} BTC")
        print(f"Sell volume: {sell_vol:,.6f} BTC")
        print(f"Buy/Sell ratio: {buy_vol / sell_vol:.2f}" if sell_vol > 0 else "No sells")

asyncio.run(main())
```
