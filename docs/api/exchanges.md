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

## Upbit

Upbit is a Korean-won (KRW) spot exchange — no sandbox/demo environment and
spot only (`market_type` must be `"spot"`, `sandbox=True` raises
`NotSupportedError`). Its native symbol format is `QUOTE-BASE` (e.g. `KRW-BTC`
for `BTC/KRW`), the reverse of most exchanges. Private endpoints are signed
with a JWT (HS256) rather than an HMAC header.

```python
from pycex import Upbit

# Public data (no auth)
with Upbit() as ex:
    ticker = ex.fetch_ticker_sync("BTC/KRW")
    ob = ex.fetch_order_book_sync("BTC/KRW", limit=10)
    print(f"BTC: ₩{ticker.last:,.0f}")

# With authentication
with Upbit(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/KRW", "buy", "limit", 0.001, 100_000_000.0)
    canceled = ex.cancel_order_sync(order.id, "BTC/KRW")
```

### Upbit Constructor

```python
Upbit(
    api_key: str = "",
    secret: str = "",
    *,
    sandbox: bool = False,      # always False — raises NotSupportedError if True
    market_type: MarketType = "spot",  # must be "spot" — raises NotSupportedError otherwise
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Upbit access key |
| `secret` | `str` | `""` | Upbit secret key |
| `sandbox` | `bool` | `False` | Not supported — Upbit has no demo environment |
| `market_type` | `"spot" \| "linear"` | `"spot"` | Only `"spot"` is supported |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Upbit Notes

- **Market orders**: a market *buy* uses Upbit's `ord_type="price"` — the
  `amount` argument to `create_order` is then the **KRW total to spend**, not
  a BTC quantity. A market *sell* uses `ord_type="market"` with `amount` as
  the base-asset volume, matching every other adapter.
- **`fetch_my_trades`**: Upbit has no dedicated fills endpoint. It flattens
  the `trades` array of completed (`state=done`) orders instead; `fee` is
  always `0.0` (not prorated from the order's `paid_fee`) — see `raw` for the
  original trade payload.
- **Daily candles reset at 00:00 UTC (09:00 KST)**, not KST midnight —
  different from Bithumb/Korbit, which reset at KST midnight.

## Bithumb

Bithumb is a Korean-won (KRW) spot exchange — no sandbox/demo environment and
spot only, same as Upbit. Its public market-data surface (symbols, candles,
ticker, order book, public trades) is identical in path and shape to Upbit's,
so both adapters share that code (`KrwV1Mixin`). Private endpoints, however,
are a **v1/v2 mix**: balance uses the same `/v1/accounts` as Upbit, but order
creation/cancel/pending/history use newer `/v2/...` paths with a leaner
response shape, while individual-order lookup stays on the legacy `/v1/order`.
Auth is a JWT (HS256) like Upbit's, but the payload requires an explicit
`timestamp` (ms) field that Upbit's omits.

```python
from pycex import Bithumb

# Public data (no auth)
with Bithumb() as ex:
    ticker = ex.fetch_ticker_sync("BTC/KRW")
    ob = ex.fetch_order_book_sync("BTC/KRW", limit=10)
    print(f"BTC: ₩{ticker.last:,.0f}")

# With authentication
with Bithumb(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/KRW", "buy", "limit", 0.001, 100_000_000.0)
    canceled = ex.cancel_order_sync(order.id, "BTC/KRW")
```

### Bithumb Constructor

```python
Bithumb(
    api_key: str = "",
    secret: str = "",
    *,
    sandbox: bool = False,      # always False — raises NotSupportedError if True
    market_type: MarketType = "spot",  # must be "spot" — raises NotSupportedError otherwise
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Bithumb access key |
| `secret` | `str` | `""` | Bithumb secret key |
| `sandbox` | `bool` | `False` | Not supported — Bithumb has no demo environment |
| `market_type` | `"spot" \| "linear"` | `"spot"` | Only `"spot"` is supported |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Bithumb Notes

- **Private endpoints mix v1 and v2 paths**: balance (`GET /v1/accounts`) and
  individual-order lookup (`GET /v1/order?uuid=`) are v1 and return the full
  order/account shape; order creation (`POST /v2/orders`), cancel
  (`DELETE /v2/order`), open orders (`GET /v2/orders/pending`), and completed
  orders (`GET /v2/orders/history`) are v2. The v2 field names (`order_id`,
  `order_type`) are normalized to their v1 equivalents (`uuid`, `ord_type`)
  before parsing, so all endpoints share one `Order` parser.
- **Market orders**: same convention as Upbit — a market *buy* uses
  `order_type="price"` with `amount` as the **KRW total to spend**; a market
  *sell* uses `order_type="market"` with `amount` as the base-asset volume.
- **`create_order`/`cancel_order` return partial data**: Bithumb's v2
  create/cancel responses don't echo back price/volume/state the way the v1
  full-order shape does, so the returned `Order`'s `amount`/`price`/`status`
  reflect only what the API actually returned (`cancel_order` forces
  `status="cancel"` since that's the one fact the call itself guarantees) —
  see `raw` for the full response.
- **`fetch_my_trades` makes `1 + N` requests**: `/v2/orders/history` has no
  `trades` array (only `trades_count`), so this fetches up to `limit`
  (default 20, capped at 50) completed orders, then calls
  `GET /v1/order?uuid=` once per order to flatten its `trades[]` array.
- 🚨 **Daily candles reset at 00:00 KST (15:00 UTC the previous day)** —
  different from Upbit, which resets at 00:00 UTC, despite both exchanges
  returning the same `candle_date_time_utc` field shape.

## Korbit

Korbit is a Korean-won (KRW) spot exchange (v2 REST) — no sandbox/demo
environment and spot only. Unlike Upbit/Bithumb (JWT-in-header), Korbit signs
with a single header (`X-KAPI-KEY`) plus two ordinary request *parameters*
that ride alongside every private call: `timestamp` (Unix ms) and `signature`
(HMAC-SHA256 hex over the exact encoded query string — GET/DELETE — or
`application/x-www-form-urlencoded` body — POST — that is actually sent,
`signature` itself excluded). Every response, public or private, is wrapped
`{"success": true/false, "data": ...}`.

🚨 **문서 확인일 2026-08-30, 서명 = HMAC-SHA256(secret, 전송될 쿼리스트링 또는 폼바디 문자열(signature 제외))**,
헤더는 `X-KAPI-KEY` 하나뿐이고 `timestamp`/`signature`는 헤더가 아니라 파라미터로 전송됨
(GET/DELETE=쿼리, POST=`application/x-www-form-urlencoded` 바디) —
`docs.korbit.co.kr/llms/en/rest_api.md` · `rest_api/trading.md` · `rest_api/quotation.md` 직접 열람으로 확인.

```python
from pycex import Korbit

# Public data (no auth)
with Korbit() as ex:
    ticker = ex.fetch_ticker_sync("BTC/KRW")
    candles = ex.fetch_candles_sync("BTC/KRW", "1d", limit=3)
    print(f"BTC: ₩{ticker.last:,.0f}")

# With authentication
with Korbit(api_key="KEY", secret="SECRET") as ex:
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC/KRW", "buy", "limit", 0.001, 100_000_000.0)
    canceled = ex.cancel_order_sync(order.id, "BTC/KRW")
```

### Korbit Constructor

```python
Korbit(
    api_key: str = "",
    secret: str = "",
    *,
    sandbox: bool = False,      # always False — raises NotSupportedError if True
    market_type: MarketType = "spot",  # must be "spot" — raises NotSupportedError otherwise
    timeout: float = 30.0,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `""` | Korbit API key (sent as `X-KAPI-KEY` header) |
| `secret` | `str` | `""` | Korbit API secret (HMAC-SHA256 signing key) |
| `sandbox` | `bool` | `False` | Not supported — Korbit has no demo environment |
| `market_type` | `"spot" \| "linear"` | `"spot"` | Only `"spot"` is supported |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds |

### Korbit Notes

- **Auth is param-based, not header-based**: only `X-KAPI-KEY` is a header;
  `timestamp` and `signature` are request parameters, computed by
  `pycex.auth.korbit_sign` over the *exact* string that will be sent
  (`HTTPClient.post_form` was added specifically so the signed bytes and the
  wire bytes are guaranteed identical — see its docstring).
- **Symbols**: `btc_krw` (lowercase, underscore) — different from
  Upbit/Bithumb's `KRW-BTC`.
- **Candle `interval`**: `1,5,15,60,240,1D` (minutes for the numeric values;
  `4h` → `240`, not `4h`). Confirmed against the live docs — the sidebar
  shorthand (`1m/5m/.../4h/1D`) the initial spec-sheet research flagged as
  unverified does **not** match the actual parameter values.
- 🚨 **`fetch_markets` active flag deviates from the original brief**: the real
  `GET /v2/currencyPairs` `status` field is `"launched"` / `"stopped"`, not
  `"active"` / `"inactive"` — confirmed against both the Task-0 fixture and a
  live docs fetch. `Market.active` is `True` iff `status == "launched"`.
- **Order amount parameter**: limit orders and market sells send `qty`
  (base-asset quantity); market buys send `amt` (quote-currency total to
  spend) — same buy/sell asymmetry as Upbit/Bithumb, different parameter names.
- **`fetch_open_orders`/`fetch_my_trades` require a symbol**: Korbit's API has
  no all-symbols listing for these (unlike Upbit/Bithumb); passing `symbol=None`
  raises `NotSupportedError`.
- **`cancel_order` returns unguessed side/type**: `DELETE /v2/orders` responds
  `{"success": true}` only, so the returned `Order`'s `side`/`type` stay `""`
  rather than being fabricated — see `raw` for the actual response.
- 🚨 **Daily candles reset at 00:00 KST (15:00 UTC the previous day)** — same
  boundary as Bithumb, different from Upbit (00:00 UTC). Confirmed by
  cross-checking identical epoch values against Bithumb's fixture (see
  `tests/fixtures/NOTES.md`).

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
