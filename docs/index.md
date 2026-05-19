# pycex

**Unified Python wrapper for cryptocurrency exchanges** — Binance, Bybit, OKX.

pycex provides a clean, typed, async-first Python library for interacting with
multiple cryptocurrency exchanges through a single unified API. It features
Pydantic type safety, a built-in rate limiter, MCP server integration, and
a CLI tool.

## Features

- **Unified API** — the same interface across Binance, Bybit, and OKX
- **Sync + Async** — both synchronous and asynchronous usage
- **Pydantic Models** — typed responses: `Ticker`, `OrderBook`, `Balance`, `Order`, `Candle`, `Trade`
- **Rate Limiting** — token bucket rate limiter built into the HTTP client
- **MCP Server** — connect to Claude Desktop and other AI assistants
- **CLI** — terminal-based exchange operations
- **Type Safe** — PEP 561 `py.typed`, complete type annotations

## Quick Example

Fetch the current BTC price from Binance with no API key required:

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(f"BTC: ${ticker.last:,.2f}")
    print(f"  Bid: ${ticker.bid:,.2f}")
    print(f"  Ask: ${ticker.ask:,.2f}")
    print(f"  24h Volume: {ticker.volume:,.2f}")
```

Switch to any exchange with the same code:

```python
from pycex import Binance, Bybit, OKX

for ExchangeClass in [Binance, Bybit, OKX]:
    with ExchangeClass() as ex:
        ticker = ex.fetch_ticker_sync("BTCUSDT" if ex.name != "okx" else "BTC-USDT")
        print(f"{ex.name}: BTC = ${ticker.last:,.2f}")
```

Async usage with `asyncio`:

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        ticker = await ex.fetch_ticker("BTCUSDT")
        ob = await ex.fetch_order_book("BTCUSDT", limit=5)

        print(f"BTC: ${ticker.last:,.2f}")
        print(f"Best bid: ${ob.bids[0].price:,.2f} x {ob.bids[0].amount}")

asyncio.run(main())
```

## Supported Exchanges

| Exchange | Symbol Format | Testnet |
|----------|--------------|---------|
| Binance  | `BTCUSDT`    | `testnet=True` |
| Bybit    | `BTCUSDT`    | `testnet=True` |
| OKX      | `BTC-USDT`   | `demo=True` |

## Installation

```bash
pip install pycex
```

With MCP server support:

```bash
pip install pycex[mcp]
```
