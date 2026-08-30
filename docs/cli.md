# CLI

pycex includes a command-line interface for quick exchange interactions
from the terminal.

Supported exchanges: `binance`, `bybit`, `okx`, `bitget`, `upbit`, `bithumb`,
`korbit`. All seven go through the same `pycex.factory.create_exchange`
factory the MCP server uses, so both entry points stay in sync.

## Setup

Set environment variables for the exchange, API key, and secret:

```bash
export PYCEX_EXCHANGE=binance
export PYCEX_API_KEY="your_api_key"
export PYCEX_SECRET="your_secret"
```

Or pass them as command-line arguments:

```bash
pycex --exchange binance --api-key "KEY" --secret "SECRET" ticker BTC/USDT
```

Symbols are always the canonical `BASE/QUOTE` notation (spot, e.g. `BTC/USDT`,
`BTC/KRW`) or `BASE/QUOTE:SETTLE` (linear, e.g. `BTC/USDT:USDT`) — never the
exchange's own native notation (`BTCUSDT`, `BTC-USDT`, `KRW-BTC`, `btc_krw`,
...). Passing a native symbol raises `SymbolNotFoundError`.

Per-exchange env vars are also honored when `--api-key`/`--secret`/
`PYCEX_API_KEY`/`PYCEX_SECRET` are left unset — useful for keeping several
exchanges' credentials configured at once:

```bash
export PYCEX_BYBIT_API_KEY="bybit_key"
export PYCEX_BYBIT_SECRET="bybit_secret"
export PYCEX_OKX_API_KEY="okx_key"
export PYCEX_OKX_SECRET="okx_secret"
export PYCEX_OKX_PASSPHRASE="okx_passphrase"   # OKX and Bitget only
```

## Commands

### ticker

Get current price for a trading pair:

```bash
# Default exchange (binance)
pycex ticker BTC/USDT

# Specify exchange
pycex -e bybit ticker BTC/USDT
pycex -e okx ticker BTC/USDT
pycex -e upbit ticker BTC/KRW

# JSON output
pycex --json ticker BTC/USDT
```

Example output:

```
BTC/USDT
  Last: 67,000  Bid: 66,999  Ask: 67,001
  High: 68,500  Low: 65,200
  Volume: 12,345.67
```

### orderbook

Get the order book (bid/ask levels):

```bash
pycex orderbook BTC/USDT

# JSON output
pycex --json orderbook ETH/USDT
```

Example output:

```
Order Book: BTC/USDT
  ASK
        67,050  1.234
        67,025  0.567
        67,010  2.345
  ---
        66,990  3.456
        66,975  1.234
        66,950  0.890
  BID
```

### balance

Get your account balance (requires API key):

```bash
pycex balance

# JSON output
pycex --json balance
```

Example output:

```
Balance:
      BTC: free=0.5, locked=0.01, total=0.51
     USDT: free=10000, locked=500, total=10500
```

### buy

Place a limit buy order:

```bash
# pycex buy <symbol> <amount> <price>
pycex buy BTC/USDT 0.001 50000

# Sandbox/testnet/demo mode
pycex --sandbox buy BTC/USDT 0.001 50000
```

Example output:

```
Buy order placed: id=12345678, BTC/USDT, amount=0.001, price=50000.0
```

### sell

Place a limit sell order:

```bash
# pycex sell <symbol> <amount> <price>
pycex sell BTC/USDT 0.001 70000

# Sandbox with JSON output
pycex --sandbox --json sell BTC/USDT 0.001 70000
```

Example output:

```
Sell order placed: id=87654321, BTC/USDT, amount=0.001, price=70000.0
```

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--exchange` | `-e` | Exchange: `binance`, `bybit`, `okx`, `bitget`, `upbit`, `bithumb`, `korbit` |
| `--api-key` | | API key (or use `PYCEX_API_KEY` / `PYCEX_{EXCHANGE}_API_KEY`) |
| `--secret` | | API secret (or use `PYCEX_SECRET` / `PYCEX_{EXCHANGE}_SECRET`) |
| `--sandbox` | | Use sandbox/testnet/demo mode |
| `--testnet` | | **Deprecated** alias for `--sandbox` (emits a `DeprecationWarning`) |
| `--market-type` | | `spot` (default) or `linear` (USDT-margined perpetuals; Binance/Bybit/OKX/Bitget only) |
| `--json` | | Output as JSON |

An unrecognized `--exchange` value exits with status 1 and prints the list of
valid names to stderr.

## Examples

Fetch tickers from multiple exchanges:

```bash
pycex -e binance ticker BTC/USDT
pycex -e bybit ticker BTC/USDT
pycex -e okx ticker BTC/USDT
pycex -e upbit ticker BTC/KRW
pycex -e bithumb ticker BTC/KRW
pycex -e korbit ticker BTC/KRW
```

Full trading workflow on sandbox:

```bash
export PYCEX_API_KEY="sandbox_key"
export PYCEX_SECRET="sandbox_secret"

# Check balance
pycex --sandbox balance

# Place buy order
pycex --sandbox buy BTC/USDT 0.001 50000

# Check balance again
pycex --sandbox --json balance
```

Linear (USDT-margined perpetual) market — Binance, OKX, and Bitget also
support `--market-type linear`; the three KRW exchanges (Upbit, Bithumb,
Korbit) are spot-only and reject `--market-type linear`:

```bash
pycex -e bybit --market-type linear ticker BTC/USDT:USDT
```

Using JSON output for scripting:

```bash
# Pipe ticker to jq
pycex --json ticker BTC/USDT | jq '.last'

# Get all balances as JSON
pycex --json balance | jq '.assets[] | select(.free > 0)'
```
