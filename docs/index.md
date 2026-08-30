# pycex

**Unified Python wrapper for cryptocurrency exchanges** — Binance, Bybit,
OKX, Bitget, Upbit, Bithumb, Korbit.

pycex provides a clean, typed, async-first Python library for interacting with
multiple cryptocurrency exchanges through a single unified API. It features
Pydantic type safety, a built-in rate limiter, MCP server integration, and
a CLI tool.

## Features

- **Unified API** — the same interface across all seven exchanges, spot and
  USDT-margined linear perpetual (`market_type="linear"` on Binance/OKX/Bitget)
- **Sync + Async** — both synchronous and asynchronous usage
- **Canonical Symbols** — `BASE/QUOTE` (spot) / `BASE/QUOTE:SETTLE` (linear)
  on every exchange, never native notation
- **Pydantic Models** — typed responses: `Ticker`, `OrderBook`, `Balance`, `Order`, `Candle`, `Trade`, `Market`, `MyTrade`, `Position`, `FundingRate`
- **Rate Limiting** — token bucket rate limiter built into the HTTP client
- **MCP Server** — connect to Claude Desktop and other AI assistants
- **CLI** — terminal-based exchange operations
- **Type Safe** — PEP 561 `py.typed`, complete type annotations, `mypy --strict` clean

## Quick Example

Fetch the current BTC price from Binance with no API key required. Symbols
are always the canonical `BASE/QUOTE` notation (e.g. `BTC/USDT`), the same
across every exchange:

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    print(f"BTC: ${ticker.last:,.2f}")
    print(f"  Bid: ${ticker.bid:,.2f}")
    print(f"  Ask: ${ticker.ask:,.2f}")
    print(f"  24h Volume: {ticker.volume:,.2f}")
```

Switch to any exchange with the same code — no per-exchange symbol formatting
needed, each adapter converts `BTC/USDT` to its own native notation internally:

```python
from pycex import Binance, Bitget, Bybit, OKX

for ExchangeClass in [Binance, Bybit, OKX, Bitget]:
    with ExchangeClass() as ex:
        ticker = ex.fetch_ticker_sync("BTC/USDT")
        print(f"{ex.name}: BTC = ${ticker.last:,.2f}")
```

Async usage with `asyncio`:

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        ticker = await ex.fetch_ticker("BTC/USDT")
        ob = await ex.fetch_order_book("BTC/USDT", limit=5)

        print(f"BTC: ${ticker.last:,.2f}")
        print(f"Best bid: ${ob.bids[0].price:,.2f} x {ob.bids[0].amount}")

asyncio.run(main())
```

## Supported Exchanges

Symbols are the same canonical notation for every exchange below — spot
`BASE/QUOTE`, linear perpetual `BASE/QUOTE:SETTLE`. "Native Format" is what
each adapter sends to the exchange's own API internally, and is not
something callers need to construct themselves.

| Exchange | Native Format (spot) | linear | Sandbox |
|----------|------------------------|:---:|---------|
| Binance  | `BTCUSDT`   | ○ | `sandbox=True` |
| Bybit    | `BTCUSDT`   | ○ | `sandbox=True` |
| OKX      | `BTC-USDT`  | ○ | `sandbox=True` |
| Bitget   | `BTCUSDT`   | ○ | `sandbox=True` |
| Upbit    | `KRW-BTC`   | ✕ | not supported (KRW spot only) |
| Bithumb  | `KRW-BTC`   | ✕ | not supported (KRW spot only) |
| Korbit   | `btc_krw`   | ✕ | not supported (KRW spot only) |

See `docs/api/exchanges.md` for the full support matrix (markets, candle
pagination, orders, balance, my_trades, positions, funding) and per-venue
quirks.

## Installation

```bash
pip install pycex
```

With MCP server support:

```bash
pip install pycex[mcp]
```
