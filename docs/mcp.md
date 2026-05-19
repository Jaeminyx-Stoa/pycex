# MCP Server

pycex includes a Model Context Protocol (MCP) server that exposes exchange
operations as tools for AI assistants like Claude Desktop.

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

For testnet/demo mode:

```bash
export PYCEX_TESTNET=true
pycex-mcp
```

## Available Tools

The MCP server exposes the following tools:

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `get_ticker` | Get current price for a trading pair | No |
| `get_order_book` | Get bid/ask order book | No |
| `get_balance` | Get account balance | Yes |
| `place_order` | Place a buy or sell order | Yes |
| `cancel_order` | Cancel an existing order | Yes |

### get_ticker

```python
# MCP tool call
get_ticker(symbol="BTCUSDT")
# Returns: {"symbol": "BTCUSDT", "last": 67000.0, "bid": 66999.0, "ask": 67001.0, ...}
```

### get_order_book

```python
# MCP tool call
get_order_book(symbol="BTCUSDT", limit=10)
# Returns: {"symbol": "BTCUSDT", "bids": [...], "asks": [...]}
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
place_order(symbol="BTCUSDT", side="buy", order_type="limit", amount=0.001, price=50000.0)
# Returns: {"id": "12345", "symbol": "BTCUSDT", "side": "buy", ...}
```

### cancel_order

```python
# MCP tool call
cancel_order(order_id="12345", symbol="BTCUSDT")
# Returns: {"id": "12345", "symbol": "BTCUSDT", "status": "canceled"}
```

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
