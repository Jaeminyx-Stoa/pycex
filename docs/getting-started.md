# Getting Started

## Installation

Install pycex from PyPI:

```bash
pip install pycex
```

With optional extras:

```bash
# MCP server for AI assistant integration
pip install pycex[mcp]

# Documentation building
pip install pycex[docs]

# Development dependencies
pip install pycex[dev]
```

## Basic Usage

Public market data requires no API key. Use a context manager to ensure
connections are properly cleaned up. Symbols are always the canonical
`BASE/QUOTE` notation (e.g. `BTC/USDT`) regardless of exchange — each adapter
converts it to that exchange's native format internally:

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    print(f"BTC: ${ticker.last:,.2f}")
    print(f"Bid: ${ticker.bid:,.2f}  Ask: ${ticker.ask:,.2f}")
    print(f"24h High: ${ticker.high:,.2f}  Low: ${ticker.low:,.2f}")
```

### Order Book

```python
from pycex import Binance

with Binance() as ex:
    ob = ex.fetch_order_book_sync("ETH/USDT", limit=10)
    print(f"ETH/USDT Order Book")
    for ask in ob.asks[:5]:
        print(f"  Ask: ${ask.price:,.2f} x {ask.amount:,.4f}")
    for bid in ob.bids[:5]:
        print(f"  Bid: ${bid.price:,.2f} x {bid.amount:,.4f}")
```

### Async Usage

The primary API is async. Use `async with` and `await`:

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        ticker = await ex.fetch_ticker("BTC/USDT")
        ob = await ex.fetch_order_book("BTC/USDT", limit=5)
        candles = await ex.fetch_candles("BTC/USDT", "1h", limit=24)
        trades = await ex.fetch_trades("BTC/USDT", limit=10)

        print(f"BTC: ${ticker.last:,.2f}")
        print(f"Best bid: ${ob.bids[0].price:,.2f}")
        print(f"Candles: {len(candles)}")
        print(f"Recent trades: {len(trades)}")

asyncio.run(main())
```

## Environment Variables

pycex reads the following environment variables (used by the CLI and MCP
server, both of which go through the shared `pycex.factory.create_exchange`):

| Variable | Description |
|----------|-------------|
| `PYCEX_EXCHANGE` | Exchange name: `binance`, `bybit`, `okx`, `bitget`, `upbit`, `bithumb`, `korbit` |
| `PYCEX_API_KEY` | API key |
| `PYCEX_SECRET` | API secret |
| `PYCEX_PASSPHRASE` | OKX/Bitget passphrase |
| `PYCEX_SANDBOX` | Set to `1` or `true` to use sandbox/testnet/demo mode |
| `PYCEX_MARKET_TYPE` | `spot` (default) or `linear` (Binance/OKX/Bitget only) |
| `PYCEX_TESTNET` | **Deprecated** — old name for `PYCEX_SANDBOX`, still accepted |

Per-exchange variants (`PYCEX_{EXCHANGE}_API_KEY`/`_SECRET`/`_PASSPHRASE`,
e.g. `PYCEX_BYBIT_API_KEY`) are used as a fallback whenever the generic
variable above is left unset — useful for keeping several exchanges'
credentials configured at once.

Example:

```bash
export PYCEX_EXCHANGE=binance
export PYCEX_API_KEY="your_api_key"
export PYCEX_SECRET="your_secret"
```

## Authenticated Endpoints

Trading and balance operations require API keys:

```python
from pycex import Binance

with Binance(api_key="YOUR_KEY", secret="YOUR_SECRET") as ex:
    balance = ex.fetch_balance_sync()
    for asset in balance.assets:
        print(f"{asset.asset}: free={asset.free}, locked={asset.locked}")

    # Place a limit buy order
    order = ex.create_order_sync("BTC/USDT", "buy", "limit", amount=0.001, price=50000.0)
    print(f"Order placed: {order.id}, status={order.status}")
```

## Testnet / Demo Mode

All exchanges support a unified `sandbox=True` flag for safe testing (the
older `testnet=`/`demo=` kwargs still work but are deprecated):

```python
from pycex import Binance, Bybit, OKX

# Binance testnet
with Binance(api_key="KEY", secret="SECRET", sandbox=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")

# Bybit testnet
with Bybit(api_key="KEY", secret="SECRET", sandbox=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")

# OKX demo mode
with OKX(api_key="KEY", secret="SECRET", passphrase="PASS", sandbox=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
```

## Raw API Responses

Every model has a `.raw` field containing the original exchange response:

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")

    # Access the original Binance API response
    print(ticker.raw)
    # {'symbol': 'BTCUSDT', 'lastPrice': '67000.00', ...}
```

## Error Handling

pycex provides a structured exception hierarchy:

```python
from pycex import Binance
from pycex.exceptions import (
    PyCexError,
    ExchangeError,
    RateLimitError,
    NetworkError,
    AuthenticationError,
)

with Binance() as ex:
    try:
        ticker = ex.fetch_ticker_sync("INVALID/SYMBOL")
    except RateLimitError:
        print("Rate limited, try again later")
    except ExchangeError as e:
        print(f"Exchange error: {e} (code={e.code})")
    except NetworkError as e:
        print(f"Network error: {e}")
    except PyCexError as e:
        print(f"pycex error: {e}")
```
