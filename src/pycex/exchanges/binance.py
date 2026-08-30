"""Binance exchange adapter."""

from __future__ import annotations

from typing import Any

from pycex.auth import binance_headers, binance_sign
from pycex.base import BaseExchange
from pycex.constants import BINANCE_BASE, BINANCE_BROKER_ID, BINANCE_TESTNET
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade

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
        testnet: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        base = BINANCE_TESTNET if testnet else BINANCE_BASE
        broker_headers: dict[str, str] = {}
        if BINANCE_BROKER_ID:
            broker_headers["X-MBX-BROKER-ID"] = BINANCE_BROKER_ID
        self._http = HTTPClient(base, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def _auth_headers(self) -> dict[str, str]:
        return binance_headers(self._api_key)

    def _signed_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return binance_sign(self._secret, params or {})

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        data = await self._http.get("/api/v3/ticker/24hr", params={"symbol": symbol})
        return _parse_ticker(data)

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = await self._http.get("/api/v3/depth", params={"symbol": symbol, "limit": limit})
        return _parse_order_book(symbol, data)

    async def fetch_candles(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {"symbol": symbol, "interval": _TIMEFRAME_MAP.get(timeframe, timeframe), "limit": limit}
        data = await self._http.get("/api/v3/klines", params=params)
        return [_parse_candle(k) for k in data]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        data = await self._http.get("/api/v3/trades", params={"symbol": symbol, "limit": limit})
        return [_parse_trade(symbol, t) for t in data]

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        params = self._signed_params()
        data = await self._http.get("/api/v3/account", params=params, headers=self._auth_headers())
        return _parse_balance(data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(amount),
        }
        if price is not None:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"
        params = self._signed_params(params)
        data = await self._http.post("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(data)

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        params = self._signed_params({"symbol": symbol, "orderId": order_id})
        data = await self._http.delete("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        params = self._signed_params({"symbol": symbol, "orderId": order_id})
        data = await self._http.get("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(data)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        p: dict[str, Any] = {}
        if symbol:
            p["symbol"] = symbol
        params = self._signed_params(p)
        data = await self._http.get("/api/v3/openOrders", params=params, headers=self._auth_headers())
        return [_parse_order(o) for o in data]

    # ── Sync ──

    def fetch_ticker_sync(self, symbol: str) -> Ticker:
        data = self._http.sync_get("/api/v3/ticker/24hr", params={"symbol": symbol})
        return _parse_ticker(data)

    def fetch_candles_sync(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {"symbol": symbol, "interval": _TIMEFRAME_MAP.get(timeframe, timeframe), "limit": limit}
        data = self._http.sync_get("/api/v3/klines", params=params)
        return [_parse_candle(k) for k in data]

    def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = self._http.sync_get("/api/v3/depth", params={"symbol": symbol, "limit": limit})
        return _parse_order_book(symbol, data)

    def fetch_balance_sync(self) -> Balance:
        params = self._signed_params()
        data = self._http.sync_get("/api/v3/account", params=params, headers=self._auth_headers())
        return _parse_balance(data)

    def create_order_sync(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(amount),
        }
        if price is not None:
            params["price"] = str(price)
            params["timeInForce"] = "GTC"
        params = self._signed_params(params)
        data = self._http.sync_post("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(data)

    def cancel_order_sync(self, order_id: str, symbol: str) -> Order:
        params = self._signed_params({"symbol": symbol, "orderId": order_id})
        data = self._http.sync_delete("/api/v3/order", params=params, headers=self._auth_headers())
        return _parse_order(data)


# ── Parsers ──


def _parse_ticker(d: dict[str, Any]) -> Ticker:
    return Ticker(
        symbol=d["symbol"],
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


def _parse_order(d: dict[str, Any]) -> Order:
    return Order(
        id=str(d.get("orderId", "")),
        symbol=d.get("symbol", ""),
        side=d.get("side", "").lower(),
        type=d.get("type", "").lower(),
        amount=float(d.get("origQty", 0)),
        price=float(d["price"]) if d.get("price") and float(d["price"]) > 0 else None,
        filled=float(d.get("executedQty", 0)),
        status=d.get("status", ""),
        timestamp=int(d.get("transactTime", 0) or d.get("time", 0)),
        raw=d,
    )
