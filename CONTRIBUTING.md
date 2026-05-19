# Contributing to pycex

Thank you for your interest in contributing to pycex! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Clone and Install

```bash
git clone https://github.com/Jaeminyx-Stoa/pycex.git
cd pycex
pip install -e ".[dev]"
```

Or with uv:

```bash
uv pip install -e ".[dev]"
```

### Optional Extras

```bash
# MCP server development
pip install -e ".[dev,mcp]"

# Documentation
pip install -e ".[dev,docs]"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ -v --cov=pycex
```

## Linting and Formatting

```bash
# Check for lint errors
ruff check src/ tests/

# Auto-fix lint errors
ruff check --fix src/ tests/

# Check formatting
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/
```

## Type Checking

```bash
mypy src/pycex/
```

## Before Submitting a PR

Run all checks to make sure everything passes:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/pycex/
pytest tests/ -v
```

## Architecture Overview

```
src/pycex/
    __init__.py          # Public API re-exports
    base.py              # BaseExchange ABC — unified interface
    http.py              # HTTPClient with rate limiter
    auth.py              # HMAC signing for each exchange
    constants.py         # URLs, sides, order types
    exceptions.py        # Exception hierarchy
    cli.py               # CLI entry point (pycex command)
    py.typed             # PEP 561 marker
    models/
        __init__.py      # Model re-exports
        ticker.py        # Ticker model
        orderbook.py     # OrderBook + OrderBookEntry
        balance.py       # Balance + BalanceEntry
        order.py         # Order model
        candle.py        # Candle (OHLCV) model
        trade.py         # Trade model
    exchanges/
        __init__.py      # Exchange re-exports
        binance.py       # Binance adapter
        bybit.py         # Bybit V5 adapter
        okx.py           # OKX V5 adapter
    mcp/
        __init__.py
        server.py        # MCP server (pycex-mcp command)
```

### Key Design Principles

1. **Unified Interface**: All exchanges implement `BaseExchange`. The same code works across Binance, Bybit, and OKX by swapping the exchange class.

2. **Pydantic Models**: Every API response is parsed into a typed Pydantic model (`Ticker`, `OrderBook`, `Order`, etc.). All models include a `.raw` field with the original exchange response.

3. **Async-First with Sync Wrappers**: The primary API is async (`fetch_ticker`, `create_order`). Each async method has a `_sync` counterpart (`fetch_ticker_sync`, `create_order_sync`).

4. **Automatic Rate Limiting**: The `HTTPClient` uses a token bucket rate limiter. Callers do not need to manage rate limits manually.

5. **Context Manager Cleanup**: Use `with` or `async with` to ensure HTTP connections are properly closed.

## Adding a New Exchange

1. Create `src/pycex/exchanges/new_exchange.py`
2. Implement a class that extends `BaseExchange`
3. Implement all abstract methods (market data, account, trading, sync wrappers)
4. Add parser functions for converting raw API responses to unified models
5. Add auth logic to `src/pycex/auth.py`
6. Export from `src/pycex/exchanges/__init__.py` and `src/pycex/__init__.py`
7. Add tests in `tests/`

Example skeleton:

```python
from pycex.base import BaseExchange
from pycex.http import HTTPClient
from pycex.models import Ticker, OrderBook, Balance, Order, Candle, Trade


class NewExchange(BaseExchange):
    name = "new_exchange"

    def __init__(self, api_key: str = "", secret: str = "", *, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._secret = secret
        self._http = HTTPClient("https://api.newexchange.com", timeout=timeout, rate=10.0)

    async def fetch_ticker(self, symbol: str) -> Ticker:
        data = await self._http.get("/v1/ticker", params={"symbol": symbol})
        return _parse_ticker(data)

    # ... implement remaining methods
```

## PR Guidelines

- One feature or fix per PR
- Include tests for new functionality
- Update `CHANGELOG.md` for user-facing changes
- Ensure all CI checks pass before requesting review
- Use descriptive commit messages

## Code Style

- Follow the existing code patterns (look at `src/pycex/exchanges/binance.py` as a reference)
- All public functions and classes need docstrings
- All function signatures need type annotations
- Maximum line length: 120 characters (configured in `pyproject.toml`)
- Import order: stdlib, third-party, local (enforced by ruff)
