"""Binance exchange adapter."""

from __future__ import annotations

from typing import Any

from pycex.auth import binance_headers, binance_sign
from pycex.base import BaseExchange
from pycex.constants import BINANCE_BASE, BINANCE_BROKER_ID, BINANCE_TESTNET, QUOTE_SUFFIXES
from pycex.exceptions import NotSupportedError, SymbolNotFoundError
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.market import Market
from pycex.models.mytrade import MyTrade
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade
from pycex.symbols import MarketType, parse_symbol

_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


class Binance(BaseExchange):
    name = "binance"

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        *,
        sandbox: bool = False,
        market_type: MarketType = "spot",
        testnet: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        self.market_type = market_type
        self.sandbox = self._resolve_sandbox(sandbox, testnet, None)
        self._markets: dict[str, Market] = {}
        base = BINANCE_TESTNET if self.sandbox else BINANCE_BASE
        broker_headers: dict[str, str] = {}
        if BINANCE_BROKER_ID:
            broker_headers["X-MBX-BROKER-ID"] = BINANCE_BROKER_ID
        self._http = HTTPClient(base, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def to_native(self, symbol: str) -> str:
        sym = parse_symbol(symbol)
        return f"{sym.base}{sym.quote}"

    def from_native(self, native: str) -> str:
        if native in self._markets:
            return self._markets[native].symbol
        for quote in QUOTE_SUFFIXES:
            if native.endswith(quote) and len(native) > len(quote):
                return f"{native[: -len(quote)]}/{quote}"
        raise SymbolNotFoundError(f"cannot resolve native symbol {native!r} for {self.name}")

    def _auth_headers(self) -> dict[str, str]:
        return binance_headers(self._api_key)

    def _signed_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return binance_sign(self._secret, params or {})

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v3/ticker/24hr", params={"symbol": native})
        return _parse_ticker(symbol, data)

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v3/depth", params={"symbol": native, "limit": limit})
        return _parse_order_book(symbol, data)

    async def _fetch_candles_page(
        self, native: str, timeframe: str, *, since: int | None, until: int | None, limit: int
    ) -> list[Candle]:
        params: dict[str, Any] = {
            "symbol": native,
            "interval": _TIMEFRAME_MAP.get(timeframe, timeframe),
            "limit": limit,
        }
        if since is not None:
            params["startTime"] = since
        if until is not None:
            params["endTime"] = until
        data = await self._http.get("/api/v3/klines", params=params)
        return [_parse_candle(k) for k in data]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v3/trades", params={"symbol": native, "limit": limit})
        return [_parse_trade(symbol, t) for t in data]

    async def fetch_markets(self) -> list[Market]:
        raise NotSupportedError("binance.fetch_markets is not implemented yet")

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        params = self._signed_params()
        data = await self._http.get("/api/v3/account", params=params, headers=self._auth_headers())
        return _parse_balance(data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        native = self.to_native(symbol)
        params: dict[str, Any] = {
            "symbol": native,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(amount),
        }
        if price is not None:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"
        params = self._signed_params(params)
        data = await self._http.post("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(symbol, data)

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        native = self.to_native(symbol)
        params = self._signed_params({"symbol": native, "orderId": order_id})
        data = await self._http.delete("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(symbol, data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        native = self.to_native(symbol)
        params = self._signed_params({"symbol": native, "orderId": order_id})
        data = await self._http.get("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(symbol, data)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        p: dict[str, Any] = {}
        if symbol:
            p["symbol"] = self.to_native(symbol)
        params = self._signed_params(p)
        data = await self._http.get("/api/v3/openOrders", params=params, headers=self._auth_headers())
        return [_parse_order(self.from_native(o.get("symbol", "")), o) for o in data]

    async def fetch_my_trades(
        self, symbol: str | None = None, *, since: int | None = None, limit: int | None = None
    ) -> list[MyTrade]:
        raise NotSupportedError("binance.fetch_my_trades is not implemented yet")


# ── Parsers ──


def _parse_ticker(symbol: str, d: dict[str, Any]) -> Ticker:
    return Ticker(
        symbol=symbol,
        last=float(d["lastPrice"]),
        bid=float(d["bidPrice"]),
        ask=float(d["askPrice"]),
        high=float(d["highPrice"]),
        low=float(d["lowPrice"]),
        volume=float(d["volume"]),
        quote_volume=float(d.get("quoteVolume", 0)),
        timestamp=int(d.get("closeTime", 0)),
        raw=d,
    )


def _parse_order_book(symbol: str, d: dict[str, Any]) -> OrderBook:
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(b[0]), amount=float(b[1])) for b in d.get("bids", [])],
        asks=[OrderBookEntry(price=float(a[0]), amount=float(a[1])) for a in d.get("asks", [])],
        raw=d,
    )


def _parse_candle(k: list[Any]) -> Candle:
    return Candle(
        timestamp=int(k[0]),
        open=float(k[1]),
        high=float(k[2]),
        low=float(k[3]),
        close=float(k[4]),
        volume=float(k[5]),
    )


def _parse_trade(symbol: str, t: dict[str, Any]) -> Trade:
    return Trade(
        id=str(t["id"]),
        symbol=symbol,
        side="buy" if t.get("isBuyerMaker") else "sell",
        price=float(t["price"]),
        amount=float(t["qty"]),
        timestamp=int(t.get("time", 0)),
    )


def _parse_balance(d: dict[str, Any]) -> Balance:
    entries = []
    for b in d.get("balances", []):
        free = float(b["free"])
        locked = float(b["locked"])
        if free > 0 or locked > 0:
            entries.append(BalanceEntry(asset=b["asset"], free=free, locked=locked))
    return Balance(assets=entries, raw=d)


def _parse_order(symbol: str, d: dict[str, Any]) -> Order:
    return Order(
        id=str(d.get("orderId", "")),
        symbol=symbol,
        side=d.get("side", "").lower(),
        type=d.get("type", "").lower(),
        amount=float(d.get("origQty", 0)),
        price=float(d["price"]) if d.get("price") and float(d["price"]) > 0 else None,
        filled=float(d.get("executedQty", 0)),
        status=d.get("status", ""),
        timestamp=int(d.get("transactTime", 0) or d.get("time", 0)),
        raw=d,
    )
