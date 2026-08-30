"""Base exchange interface — unified API that all exchange adapters implement."""

from __future__ import annotations

import asyncio
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pycex.exceptions import NotSupportedError

if TYPE_CHECKING:
    from pycex.http import HTTPClient
    from pycex.models import Balance, Candle, FundingRate, Market, MyTrade, Order, OrderBook, Position, Ticker, Trade
    from pycex.symbols import MarketType

# Public async methods that get an auto-generated `<name>_sync` twin via __init_subclass__.
_SYNC_TARGETS = (
    "fetch_ticker",
    "fetch_order_book",
    "fetch_candles",
    "fetch_trades",
    "fetch_markets",
    "fetch_balance",
    "create_order",
    "cancel_order",
    "fetch_order",
    "fetch_open_orders",
    "fetch_my_trades",
    "fetch_positions",
    "fetch_funding_rate",
)


def _make_sync(name: str) -> Callable[..., Any]:
    def _sync(self: BaseExchange, *a: Any, **kw: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(getattr(self, name)(*a, **kw))
        raise RuntimeError(f"{name}_sync called inside a running event loop; await {name}() instead")

    _sync.__name__ = f"{name}_sync"
    return _sync


class BaseExchange(ABC):
    """Abstract base class for exchange implementations.

    All exchanges expose the same unified interface. Use the concrete classes
    (Binance, Bybit, OKX, Bitget) which implement these methods. Every public
    async method listed in ``_SYNC_TARGETS`` gets a blocking ``<name>_sync``
    twin generated automatically for each subclass (see ``__init_subclass__``).
    """

    name: str = ""
    market_type: MarketType = "spot"
    sandbox: bool = False
    candle_page_limit: int = 200
    supported_timeframes: frozenset[str] = frozenset({"1m", "5m", "15m", "1h", "4h", "1d"})
    _http: HTTPClient

    if TYPE_CHECKING:
        # Declared for static typing only — the real implementations are
        # generated at runtime by __init_subclass__ (see _make_sync above).
        def fetch_ticker_sync(self, symbol: str) -> Ticker: ...
        def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook: ...
        def fetch_candles_sync(
            self,
            symbol: str,
            timeframe: str = "1h",
            *,
            since: int | None = None,
            until: int | None = None,
            limit: int | None = None,
        ) -> list[Candle]: ...
        def fetch_trades_sync(self, symbol: str, *, limit: int = 100) -> list[Trade]: ...
        def fetch_markets_sync(self) -> list[Market]: ...
        def fetch_balance_sync(self) -> Balance: ...
        def create_order_sync(
            self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
        ) -> Order: ...
        def cancel_order_sync(self, order_id: str, symbol: str) -> Order: ...
        def fetch_order_sync(self, order_id: str, symbol: str) -> Order: ...
        def fetch_open_orders_sync(self, symbol: str | None = None) -> list[Order]: ...
        def fetch_my_trades_sync(
            self, symbol: str | None = None, *, since: int | None = None, limit: int | None = None
        ) -> list[MyTrade]: ...
        def fetch_positions_sync(self, symbols: list[str] | None = None) -> list[Position]: ...
        def fetch_funding_rate_sync(self, symbol: str) -> FundingRate: ...

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        for n in _SYNC_TARGETS:
            if f"{n}_sync" not in cls.__dict__:
                setattr(cls, f"{n}_sync", _make_sync(n))

    @staticmethod
    def _resolve_sandbox(sandbox: bool, testnet: bool | None, demo: bool | None) -> bool:
        """Map the deprecated ``testnet=``/``demo=`` kwargs onto ``sandbox=``."""
        if testnet is not None or demo is not None:
            warnings.warn("testnet=/demo= are deprecated; use sandbox=", DeprecationWarning, stacklevel=3)
            return bool(sandbox or testnet or demo)
        return sandbox

    # ── Symbols ──

    @abstractmethod
    def to_native(self, symbol: str) -> str:
        """Convert a canonical symbol (``BASE/QUOTE`` or ``BASE/QUOTE:SETTLE``) to exchange notation."""
        ...

    @abstractmethod
    def from_native(self, native: str) -> str:
        """Convert an exchange-native symbol back to canonical notation."""
        ...

    # ── Market Data ──

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker: ...

    @abstractmethod
    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook: ...

    @abstractmethod
    async def _fetch_candles_page(
        self, native: str, timeframe: str, *, since: int | None, until: int | None, limit: int
    ) -> list[Candle]:
        """Fetch a single page of candles in exchange-native notation. Adapters implement this hook."""
        ...

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        *,
        since: int | None = None,
        until: int | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Fetch OHLCV candles, paginating over ``_fetch_candles_page`` when ``since``/``until`` are given."""
        if timeframe not in self.supported_timeframes:
            raise NotSupportedError(f"{self.name} does not support timeframe {timeframe}")
        native = self.to_native(symbol)
        if since is None:
            return await self._fetch_candles_page(native, timeframe, since=None, until=until, limit=limit or 100)
        out: dict[int, Candle] = {}
        cursor = since
        while True:
            page = await self._fetch_candles_page(
                native, timeframe, since=cursor, until=until, limit=self.candle_page_limit
            )
            page = [c for c in page if c.timestamp >= since and (until is None or c.timestamp <= until)]
            if not page:
                break
            new = [c for c in page if c.timestamp not in out]
            for c in new:
                out[c.timestamp] = c
            if (
                not new
                or (until is not None and max(c.timestamp for c in page) >= until)
                or len(page) < self.candle_page_limit
            ):
                break
            cursor = max(c.timestamp for c in page) + 1
            if limit is not None and len(out) >= limit:
                break
        result = [out[k] for k in sorted(out)]
        return result[:limit] if limit else result

    @abstractmethod
    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]: ...

    @abstractmethod
    async def fetch_markets(self) -> list[Market]: ...

    # ── Account ──

    @abstractmethod
    async def fetch_balance(self) -> Balance: ...

    async def fetch_positions(self, symbols: list[str] | None = None) -> list[Position]:
        raise NotSupportedError(f"{self.name}:{self.market_type} has no positions")

    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        raise NotSupportedError(f"{self.name}:{self.market_type} has no funding rate")

    # ── Trading ──

    @abstractmethod
    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Order: ...

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Order: ...

    @abstractmethod
    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]: ...

    @abstractmethod
    async def fetch_my_trades(
        self, symbol: str | None = None, *, since: int | None = None, limit: int | None = None
    ) -> list[MyTrade]: ...

    # ── Lifecycle ──

    async def close(self) -> None:
        await self._http.close()

    def close_sync(self) -> None:
        self._http.sync_close()

    async def __aenter__(self) -> BaseExchange:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def __enter__(self) -> BaseExchange:
        return self

    def __exit__(self, *args: object) -> None:
        self.close_sync()
