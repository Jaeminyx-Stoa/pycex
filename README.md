# pycex

Unified Python wrapper for cryptocurrency exchanges — **Binance**, **Bybit**, **OKX**.

ccxt의 복잡한 코드베이스 대신, Pydantic 타입 안전성과 async-first 설계, 내장 rate limiter, MCP 서버를 제공하는 깔끔한 Python 라이브러리입니다.

## Features

- **Unified API** — 동일한 인터페이스로 3개 거래소 사용
- **Sync + Async** — 동기/비동기 모두 지원
- **Pydantic Models** — `Ticker`, `OrderBook`, `Balance`, `Order`, `Candle`, `Trade`
- **Rate Limiting** — Token bucket rate limiter 내장
- **MCP Server** — Claude Desktop 등 AI 어시스턴트 연동
- **CLI** — 터미널에서 시세, 잔고, 주문
- **Type Safe** — PEP 561 `py.typed`, 완전한 타입 힌트

## Installation

```bash
pip install pycex

# MCP 서버 사용 시
pip install pycex[mcp]
```

## Quick Start

```python
from pycex import Binance

# 시세 조회 (인증 불필요)
with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(f"BTC: ${ticker.last:,.2f}")
    print(f"  Bid: ${ticker.bid:,.2f}  Ask: ${ticker.ask:,.2f}")
    print(f"  24h High: ${ticker.high:,.2f}  Low: ${ticker.low:,.2f}")
    print(f"  Volume: {ticker.volume:,.2f}")
```

## Multi-Exchange

동일한 인터페이스로 거래소를 교체할 수 있습니다:

```python
from pycex import Binance, Bybit, OKX

# 같은 코드로 다른 거래소 사용
for ExchangeClass in [Binance, Bybit, OKX]:
    with ExchangeClass() as ex:
        ticker = ex.fetch_ticker_sync("BTCUSDT")
        print(f"{ex.name}: BTC = ${ticker.last:,.2f}")
```

## Async Usage

```python
import asyncio
from pycex import Binance

async def main():
    async with Binance() as ex:
        ticker = await ex.fetch_ticker("BTCUSDT")
        ob = await ex.fetch_order_book("BTCUSDT", limit=5)
        candles = await ex.fetch_candles("BTCUSDT", "1h", limit=24)

        print(f"BTC: ${ticker.last:,.2f}")
        print(f"Best bid: ${ob.bids[0].price:,.2f} × {ob.bids[0].amount}")
        print(f"Last 24 candles: {len(candles)}")

asyncio.run(main())
```

## Order Book

```python
from pycex import Binance

with Binance() as ex:
    ob = ex.fetch_order_book_sync("ETHUSDT", limit=10)
    print("Asks:")
    for ask in ob.asks[:5]:
        print(f"  ${ask.price:,.2f} × {ask.amount:,.4f}")
    print("Bids:")
    for bid in ob.bids[:5]:
        print(f"  ${bid.price:,.2f} × {bid.amount:,.4f}")
```

## Trading

```python
from pycex import Binance

with Binance(api_key="YOUR_KEY", secret="YOUR_SECRET", testnet=True) as ex:
    # 잔고 조회
    balance = ex.fetch_balance_sync()
    btc = balance.get("BTC")
    if btc:
        print(f"BTC: free={btc.free}, locked={btc.locked}, total={btc.total}")

    # Limit 매수
    order = ex.create_order_sync("BTCUSDT", "buy", "limit", amount=0.001, price=50000.0)
    print(f"Order placed: {order.id}")

    # 주문 취소
    canceled = ex.cancel_order_sync(order.id, "BTCUSDT")
    print(f"Canceled: {canceled.id}")
```

## Candles (OHLCV)

```python
from pycex import Bybit

with Bybit() as ex:
    candles = ex.fetch_order_book_sync("BTCUSDT", limit=5)
    # 일봉
    candles = ex.fetch_candles("BTCUSDT", "1d", limit=30)  # async
```

지원 timeframe: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

## Bybit

```python
from pycex import Bybit

with Bybit(api_key="KEY", secret="SECRET") as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTCUSDT", "buy", "limit", 0.001, 50000.0)
```

## OKX

```python
from pycex import OKX

with OKX(api_key="KEY", secret="SECRET", passphrase="PASS") as ex:
    ticker = ex.fetch_ticker_sync("BTC-USDT")
    balance = ex.fetch_balance_sync()
    order = ex.create_order_sync("BTC-USDT", "buy", "limit", 0.001, 50000.0)
```

## Raw API Response

모든 모델은 `.raw` 필드로 원본 거래소 응답에 접근할 수 있습니다:

```python
from pycex import Binance

with Binance() as ex:
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(ticker.raw)  # Original Binance API response dict
```

## CLI

```bash
export PYCEX_EXCHANGE=binance
export PYCEX_API_KEY="your_key"
export PYCEX_SECRET="your_secret"

pycex ticker BTCUSDT              # 시세 조회
pycex orderbook BTCUSDT           # 호가창
pycex balance                     # 잔고
pycex buy BTCUSDT 0.001 50000     # 매수
pycex sell BTCUSDT 0.001 55000    # 매도

# 거래소 지정
pycex -e bybit ticker BTCUSDT
pycex -e okx ticker BTC-USDT

# Testnet + JSON
pycex --testnet --json ticker BTCUSDT
```

## MCP Server (Claude Desktop)

`claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "crypto": {
            "command": "pycex-mcp",
            "env": {
                "PYCEX_EXCHANGE": "binance",
                "PYCEX_API_KEY": "your_key",
                "PYCEX_SECRET": "your_secret"
            }
        }
    }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_ticker` | 시세 조회 |
| `get_order_book` | 호가창 조회 |
| `get_balance` | 잔고 조회 |
| `place_order` | 매수/매도 주문 |
| `cancel_order` | 주문 취소 |

## Supported Exchanges

| Exchange | Symbol Format | Testnet |
|----------|--------------|---------|
| Binance | `BTCUSDT` | `testnet=True` |
| Bybit | `BTCUSDT` | `testnet=True` |
| OKX | `BTC-USDT` | `demo=True` |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PYCEX_EXCHANGE` | 거래소 이름 (`binance`, `bybit`, `okx`) |
| `PYCEX_API_KEY` | API 키 |
| `PYCEX_SECRET` | API 시크릿 |
| `PYCEX_PASSPHRASE` | OKX passphrase |
| `PYCEX_TESTNET` | `1`/`true` — 테스트넷 사용 |

## License

MIT
