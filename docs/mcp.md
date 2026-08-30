# MCP Server

pycex includes a Model Context Protocol (MCP) server that exposes exchange
operations as tools for AI assistants like Claude Desktop.

Exchange construction goes through the same `pycex.factory.create_exchange`
factory the CLI uses (`binance`, `bybit`, `okx`, `bitget`, `upbit`, `bithumb`,
`korbit`), so both entry points always agree on supported exchanges and env
var resolution.

## Installation

```bash
pip install pycex[mcp]
```

## Claude Desktop Setup

Add the following to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "crypto": {
            "command": "pycex-mcp",
            "env": {
                "PYCEX_EXCHANGE": "binance",
                "PYCEX_API_KEY": "your_api_key",
                "PYCEX_SECRET": "your_secret"
            }
        }
    }
}
```

For OKX, add the passphrase:

```json
{
    "mcpServers": {
        "crypto": {
            "command": "pycex-mcp",
            "env": {
                "PYCEX_EXCHANGE": "okx",
                "PYCEX_API_KEY": "your_api_key",
                "PYCEX_SECRET": "your_secret",
                "PYCEX_PASSPHRASE": "your_passphrase"
            }
        }
    }
}
```

## Running the Server

The MCP server runs over stdio:

```bash
# Start the server (uses PYCEX_* environment variables)
export PYCEX_EXCHANGE=binance
export PYCEX_API_KEY="your_key"
export PYCEX_SECRET="your_secret"
pycex-mcp
```

For sandbox/testnet/demo mode:

```bash
export PYCEX_SANDBOX=true
pycex-mcp
```

`PYCEX_TESTNET=true` is still accepted as a deprecated alias for
`PYCEX_SANDBOX` (kept for existing configs). For linear (USDT-margined
perpetual) markets:

```bash
export PYCEX_MARKET_TYPE=linear
pycex-mcp
```

Per-exchange env vars (`PYCEX_{EXCHANGE}_API_KEY`/`_SECRET`/`_PASSPHRASE`,
e.g. `PYCEX_BYBIT_API_KEY`) are used as a fallback whenever the generic
`PYCEX_API_KEY`/`PYCEX_SECRET`/`PYCEX_PASSPHRASE` are left unset — the same
resolution order the CLI uses (see `docs/cli.md`).

## Available Tools

The MCP server exposes the following tools. `get_ticker`, `get_order_book`,
`get_balance`, `place_order`, `cancel_order`, and `analyze_chart` operate on
the single exchange configured via `PYCEX_EXCHANGE`/env vars (see above).
`compare_prices` and `aggregate_balance` fan out across multiple exchanges at
once (see below).

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `get_ticker` | Get current price for a trading pair | No |
| `get_order_book` | Get bid/ask order book | No |
| `get_balance` | Get account balance | Yes |
| `place_order` | Place a buy or sell order | Yes |
| `cancel_order` | Cancel an existing order | Yes |
| `compare_prices` | Compare a symbol's price across multiple exchanges, flag arbitrage spreads | No |
| `analyze_chart` | SMA/RSI/Bollinger Bands/support-resistance technical analysis | No |
| `aggregate_balance` | Combine balances across every exchange with credentials configured | Yes (per exchange) |

### get_ticker

```python
# MCP tool call — symbol is always canonical BASE/QUOTE, e.g. "BTC/USDT"
get_ticker(symbol="BTC/USDT")
# Returns: {"symbol": "BTC/USDT", "last": 67000.0, "bid": 66999.0, "ask": 67001.0, ...}
```

### get_order_book

```python
# MCP tool call
get_order_book(symbol="BTC/USDT", limit=10)
# Returns: {"symbol": "BTC/USDT", "bids": [...], "asks": [...]}
```

### get_balance

```python
# MCP tool call
get_balance()
# Returns: {"assets": [{"asset": "BTC", "free": 0.5, "locked": 0.0, "total": 0.5}, ...]}
```

### place_order

```python
# MCP tool call — limit buy
place_order(symbol="BTC/USDT", side="buy", order_type="limit", amount=0.001, price=50000.0)
# Returns: {"id": "12345", "symbol": "BTC/USDT", "side": "buy", ...}
```

### cancel_order

```python
# MCP tool call
cancel_order(order_id="12345", symbol="BTC/USDT")
# Returns: {"id": "12345", "symbol": "BTC/USDT", "status": "canceled"}
```

### compare_prices

Fans out `fetch_ticker` across the exchanges named in
`PYCEX_COMPARE_EXCHANGES` (comma-separated, default
`binance,okx,bitget,upbit,bithumb,korbit` — Bybit excluded from the default
set) and flags a simple arbitrage spread (`spread_pct > 0.1`).

```python
# MCP tool call — canonical symbol; use "BTC/KRW" to include the KRW exchanges
compare_prices(symbol="BTC/USDT")
# Returns: {"symbol": "BTC/USDT", "exchanges": {"binance": {"price": ..., ...}, ...},
#           "arbitrage": {"buy_on": "...", "sell_on": "...", "spread_pct": ..., "profitable": ...}}
```

### analyze_chart

```python
# MCP tool call — runs against the single exchange from PYCEX_EXCHANGE
analyze_chart(symbol="BTC/USDT", timeframe="1h", period=50)
# Returns: {"current_price": ..., "sma_20": ..., "rsi_14": ..., "volatility": ...,
#           "bollinger_bands": {...}, "support": ..., "resistance": ..., "signal": "neutral", ...}
```

### aggregate_balance

Calls `fetch_balance` on every exchange in `PYCEX_COMPARE_EXCHANGES` that has
a `PYCEX_{EXCHANGE}_API_KEY` set, skipping (not erroring on) the rest.

```python
# MCP tool call
aggregate_balance()
# Returns: {"aggregated": {"BTC": {"total": ..., "free": ..., "locked": ..., "exchanges": [...]}, ...},
#           "by_exchange": {"binance": [...], "bybit": {"skipped": "PYCEX_BYBIT_API_KEY not configured"}, ...}}
```

## Prompts

The server also exposes three MCP prompts that guide an assistant through a
multi-tool workflow: `market_analysis(symbol)` (compare prices, run technical
analysis across timeframes, check the order book), `portfolio_review()`
(aggregate balance across exchanges, price each holding, assess allocation),
and `arbitrage_scan()` (scan BTC/ETH/SOL/XRP for cross-exchange spreads).

## Programmatic Usage

You can also use the MCP server components programmatically:

```python
from pycex.mcp.server import mcp, _get_exchange

# The FastMCP instance can be run directly
mcp.run(transport="stdio")
```

## Multi-Exchange Setup

To use multiple exchanges, run separate MCP server instances:

```json
{
    "mcpServers": {
        "binance": {
            "command": "pycex-mcp",
            "env": {
                "PYCEX_EXCHANGE": "binance",
                "PYCEX_API_KEY": "binance_key",
                "PYCEX_SECRET": "binance_secret"
            }
        },
        "bybit": {
            "command": "pycex-mcp",
            "env": {
                "PYCEX_EXCHANGE": "bybit",
                "PYCEX_API_KEY": "bybit_key",
                "PYCEX_SECRET": "bybit_secret"
            }
        }
    }
}
```
