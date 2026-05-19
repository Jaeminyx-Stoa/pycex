# Exchanges

All exchange classes implement the `BaseExchange` interface. You can swap
exchanges without changing your application logic.

## Binance

```python
from pycex import Binance

# Public data (no auth)
with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    ob = ex.fetch_order_book_sync("BTCUSDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication
with Binance(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTCUSDT", "buy", "limit", 0.001, 50000.0)
    canceled = ex.cancel_order_sync(order.id, "BTCUSDT")
```

### Binance Constructor

```python
Binance(
    api_key: str = "",
    secret: str = "",
    *,
    testnet: bool = False,
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Binance API key |
| `secret` | `str` | `""` | Binance API secret |
| `testnet` | `bool` | `False` | Use testnet (`testnet.binance.vision`) |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Binance Testnet

```python
from pycex import Binance

with Binance(api_key="TESTNET_KEY", secret="TESTNET_SECRET", testnet=True) as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(f"Testnet BTC: ${ticker.last:,.2f}")

    balance = ex.fetch_balance_sync()
    btc = balance.get("BTC")
    if btc:
        print(f"BTC balance: {btc.free}")
```

## Bybit

Bybit uses the V5 API. Symbol format is the same as Binance (`BTCUSDT`).

```python
from pycex import Bybit

# Public data
with Bybit() as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    ob = ex.fetch_order_book_sync("BTCUSDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication
with Bybit(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTCUSDT", "buy", "limit", 0.001, 50000.0)
```

### Bybit Constructor

```python
Bybit(
    api_key: str = "",
    secret: str = "",
    *,
    testnet: bool = False,
    timeout: float = 30.0,
    category: str = "spot",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Bybit API key |
| `secret` | `str` | `""` | Bybit API secret |
| `testnet` | `bool` | `False` | Use testnet (`api-testnet.bybit.com`) |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |
| `category` | `str` | `"spot"` | Product category (`spot`, `linear`, `inverse`) |

### Bybit Async Example

```python
import asyncio
from pycex import Bybit

async def main():
    async with Bybit() as ex:
        ticker = await ex.fetch_ticker("BTCUSDT")
        candles = await ex.fetch_candles("BTCUSDT", "1h", limit=10)
        trades = await ex.fetch_trades("BTCUSDT", limit=5)

        print(f"BTC: ${ticker.last:,.2f}")
        for c in candles[:3]:
            print(f"  O={c.open:,.2f} H={c.high:,.2f} L={c.low:,.2f} C={c.close:,.2f}")
        for t in trades[:3]:
            print(f"  {t.side} {t.amount} @ ${t.price:,.2f}")

asyncio.run(main())
```

## OKX

OKX uses the V5 API. Symbol format uses dashes: `BTC-USDT`.

```python
from pycex import OKX

# Public data
with OKX() as ex:
    ticker = ex.fetch_ticker_sync("BTC-USDT")
    ob = ex.fetch_order_book_sync("BTC-USDT", limit=10)
    print(f"BTC: ${ticker.last:,.2f}")

# With authentication (OKX requires passphrase)
with OKX(api_key="KEY", secret="SECRET", passphrase="PASS") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC-USDT", "buy", "limit", 0.001, 50000.0)
```

### OKX Constructor

```python
OKX(
    api_key: str = "",
    secret: str = "",
    passphrase: str = "",
    *,
    demo: bool = False,
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | OKX API key |
| `secret` | `str` | `""` | OKX API secret |
| `passphrase` | `str` | `""` | OKX API passphrase |
| `demo` | `bool` | `False` | Use demo trading mode |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### OKX Demo Trading

```python
from pycex import OKX

# Demo mode uses a header flag, same API endpoint
with OKX(api_key="KEY", secret="SECRET", passphrase="PASS", demo=True) as ex:
    ticker = ex.fetch_ticker_sync("BTC-USDT")
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
ticker = await ex.fetch_ticker("BTCUSDT")
ob = await ex.fetch_order_book("BTCUSDT", limit=20)
candles = await ex.fetch_candles("BTCUSDT", "1h", limit=100)
trades = await ex.fetch_trades("BTCUSDT", limit=100)

# Sync
ticker = ex.fetch_ticker_sync("BTCUSDT")
ob = ex.fetch_order_book_sync("BTCUSDT", limit=20)
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
order = await ex.create_order("BTCUSDT", "buy", "limit", 0.001, 50000.0)
canceled = await ex.cancel_order(order.id, "BTCUSDT")
status = await ex.fetch_order(order.id, "BTCUSDT")
open_orders = await ex.fetch_open_orders("BTCUSDT")

# Sync
order = ex.create_order_sync("BTCUSDT", "buy", "limit", 0.001, 50000.0)
canceled = ex.cancel_order_sync(order.id, "BTCUSDT")
```

### Timeframes

Supported timeframes for candles: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

```python
from pycex import Binance

with Binance() as ex:
    hourly = ex.fetch_ticker_sync("BTCUSDT")
    # Use with fetch_candles
    # candles = await ex.fetch_candles("BTCUSDT", "4h", limit=50)
```
