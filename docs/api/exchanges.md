# Exchanges

All exchange classes implement the `BaseExchange` interface. You can swap
exchanges without changing your application logic. Symbols are always the
canonical `BASE/QUOTE` notation (e.g. `BTC/USDT`) — each adapter converts it
to that exchange's own native notation internally before calling the API.

## Binance

```python
from pycex import Binance

# Public data (no auth)
with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    ob = ex.fetch_order_book_sync("BTC/USDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication
with Binance(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    canceled = ex.cancel_order_sync(order.id, "BTC/USDT")
```

### Binance Constructor

```python
Binance(
    api_key: str = "",
    secret: str = "",
    *,
    sandbox: bool = False,
    market_type: MarketType = "spot",
    testnet: bool | None = None,  # deprecated, use sandbox=
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Binance API key |
| `secret` | `str` | `""` | Binance API secret |
| `sandbox` | `bool` | `False` | Use testnet (`testnet.binance.vision`) |
| `market_type` | `"spot" \| "linear"` | `"spot"` | Product type |
| `testnet` | `bool \| None` | `None` | Deprecated alias for `sandbox` |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Binance Testnet

```python
from pycex import Binance

with Binance(api_key="TESTNET_KEY", secret="TESTNET_SECRET", sandbox=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    print(f"Testnet BTC: ${ticker.last:,.2f}")

    balance = ex.fetch_balance_sync()
    btc = balance.get("BTC")
    if btc:
        print(f"BTC balance: {btc.free}")
```

## Bybit

Bybit uses the V5 API. Its native symbol format is the same as Binance
(`BTCUSDT`), but callers always pass the canonical `BTC/USDT` form.

```python
from pycex import Bybit

# Public data
with Bybit() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    ob = ex.fetch_order_book_sync("BTC/USDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication
with Bybit(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/USDT", "buy", "limit", 0.001, 50000.0)
```

### Bybit Constructor

```python
Bybit(
    api_key: str = "",
    secret: str = "",
    *,
    sandbox: bool = False,
    market_type: MarketType = "spot",
    testnet: bool | None = None,  # deprecated, use sandbox=
    timeout: float = 30.0,
    category: str | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Bybit API key |
| `secret` | `str` | `""` | Bybit API secret |
| `sandbox` | `bool` | `False` | Use testnet (`api-testnet.bybit.com`) |
| `market_type` | `"spot" \| "linear"` | `"spot"` | `"linear"` maps `category` to `"linear"` unless `category=` is given explicitly |
| `testnet` | `bool \| None` | `None` | Deprecated alias for `sandbox` |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |
| `category` | `str \| None` | `None` | Product category (`spot`, `linear`, `inverse`); overrides `market_type` when set |

### Bybit Async Example

```python
import asyncio
from pycex import Bybit

async def main():
    async with Bybit() as ex:
        ticker = await ex.fetch_ticker("BTC/USDT")
        candles = await ex.fetch_candles("BTC/USDT", "1h", limit=10)
        trades = await ex.fetch_trades("BTC/USDT", limit=5)

        print(f"BTC: ${ticker.last:,.2f}")
        for c in candles[:3]:
            print(f"  O={c.open:,.2f} H={c.high:,.2f} L={c.low:,.2f} C={c.close:,.2f}")
        for t in trades[:3]:
            print(f"  {t.side} {t.amount} @ ${t.price:,.2f}")

asyncio.run(main())
```

## OKX

OKX uses the V5 API. Its native symbol format uses dashes (`BTC-USDT`), but
callers always pass the canonical `BTC/USDT` form.

```python
from pycex import OKX

# Public data
with OKX() as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    ob = ex.fetch_order_book_sync("BTC/USDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication (OKX requires passphrase)
with OKX(api_key="KEY", secret="SECRET", passphrase="PASS") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/USDT", "buy", "limit", 0.001, 50000.0)
```

### OKX Constructor

```python
OKX(
    api_key: str = "",
    secret: str = "",
    passphrase: str = "",
    *,
    sandbox: bool = False,
    market_type: MarketType = "spot",
    demo: bool | None = None,  # deprecated, use sandbox=
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | OKX API key |
| `secret` | `str` | `""` | OKX API secret |
| `passphrase` | `str` | `""` | OKX API passphrase |
| `sandbox` | `bool` | `False` | Use demo trading mode |
| `market_type` | `"spot" \| "linear"` | `"spot"` | Product type |
| `demo` | `bool \| None` | `None` | Deprecated alias for `sandbox` |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### OKX Demo Trading

```python
from pycex import OKX

# Demo mode uses a header flag, same API endpoint
with OKX(api_key="KEY", secret="SECRET", passphrase="PASS", sandbox=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC/USDT")
    print(f"Demo BTC: ${ticker.last:,.2f}")

    balance = ex.fetch_balance_sync()
    for asset in balance.assets:
        print(f"  {asset.asset}: {asset.free}")
```

## Unified Interface (BaseExchange)

All exchanges implement these methods:

### Market Data (no auth required)

```python
# Async
ticker = await ex.fetch_ticker("BTC/USDT")
ob = await ex.fetch_order_book("BTC/USDT", limit=20)
candles = await ex.fetch_candles("BTC/USDT", "1h", limit=100)
trades = await ex.fetch_trades("BTC/USDT", limit=100)

# Sync
ticker = ex.fetch_ticker_sync("BTC/USDT")
ob = ex.fetch_order_book_sync("BTC/USDT", limit=20)
```

### Account (auth required)

```python
# Async
balance = await ex.fetch_balance()

# Sync
balance = ex.fetch_balance_sync()
```

### Trading (auth required)

```python
# Async
order = await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
canceled = await ex.cancel_order(order.id, "BTC/USDT")
status = await ex.fetch_order(order.id, "BTC/USDT")
open_orders = await ex.fetch_open_orders("BTC/USDT")

# Sync
order = ex.create_order_sync("BTC/USDT", "buy", "limit", 0.001, 50000.0)
canceled = ex.cancel_order_sync(order.id, "BTC/USDT")
```

### Timeframes

Supported timeframes for candles: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

```python
from pycex import Binance

with Binance() as ex:
    hourly = ex.fetch_ticker_sync("BTC/USDT")
    # Use with fetch_candles
    # candles = await ex.fetch_candles("BTC/USDT", "4h", limit=50)
```
