"""Base exchange interface — unified API that all exchange adapters implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycex.http import HTTPClient
    from pycex.models import Balance, Candle, Order, OrderBook, Ticker, Trade


class BaseExchange(ABC):
    """Abstract base class for exchange implementations.

    All exchanges expose the same unified interface. Use the concrete classes
    (Binance, Bybit, OKX) which implement these methods.
    """

    name: str = ""
    _http: HTTPClient

    # ── Market Data ──

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker: ...

    @abstractmethod
    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook: ...

    @abstractmethod
    async def fetch_candles(
        self, symbol: str, timeframe: str = "1h", *, limit: int = 100
    ) -> list[Candle]: ...

    @abstractmethod
    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]: ...

    # ── Account ──

    @abstractmethod
    async def fetch_balance(self) -> Balance: ...

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

    # ── Sync wrappers ──

    @abstractmethod
    def fetch_ticker_sync(self, symbol: str) -> Ticker: ...

    @abstractmethod
    def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook: ...

    @abstractmethod
    def fetch_balance_sync(self) -> Balance: ...

    @abstractmethod
    def create_order_sync(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order: ...

    @abstractmethod
    def cancel_order_sync(self, order_id: str, symbol: str) -> Order: ...

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
