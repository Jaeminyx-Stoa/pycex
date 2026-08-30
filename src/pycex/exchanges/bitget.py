"""Bitget V2 spot exchange adapter."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

from pycex.auth import bitget_headers
from pycex.base import BaseExchange
from pycex.constants import BITGET_BASE, BITGET_BROKER_ID
from pycex.exceptions import ExchangeError
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade

_TIMEFRAME_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day",
    "1w": "1week",
}


class Bitget(BaseExchange):
    """Bitget V2 spot exchange.

    Paper trading: pass ``demo=True`` to route private calls to Bitget demo
    (simulated) trading via the ``paptrading: 1`` header. Demo trading requires
    a **demo API key** issued in the Bitget demo environment.
    """

    name = "bitget"

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        passphrase: str = "",
        *,
        demo: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self._demo = demo
        broker_headers: dict[str, str] = {}
        if BITGET_BROKER_ID:
            broker_headers["X-CHANNEL-API-CODE"] = BITGET_BROKER_ID
        self._http = HTTPClient(BITGET_BASE, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def _check(self, data: dict[str, Any]) -> list[Any]:
        # Bitget wraps success as code "00000"; auth/API errors arrive as HTTP 200 + non-zero code.
        code = data.get("code", "00000")
        if code != "00000":
            raise ExchangeError(data.get("msg", "Unknown error"), code=code, exchange="bitget")
        result = data.get("data", [])
        return result if isinstance(result, list) else [result]

    def _signed_get(self, path: str) -> dict[str, str]:
        return bitget_headers(self._api_key, self._secret, self._passphrase, "GET", path, "", demo=self._demo)

    def _signed_post(self, path: str, body: str) -> dict[str, str]:
        return bitget_headers(self._api_key, self._secret, self._passphrase, "POST", path, body, demo=self._demo)

    @staticmethod
    def _path(path: str, params: dict[str, Any] | None) -> str:
        # Sign over the exact query string we send → build it into the path and pass params=None.
        return f"{path}?{urlencode(params)}" if params else path

    # ── Market Data (public, no signing) ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        data = await self._http.get("/api/v2/spot/market/tickers", params={"symbol": symbol})
        return _parse_ticker(self._check(data)[0])

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = await self._http.get("/api/v2/spot/market/orderbook", params={"symbol": symbol, "limit": limit})
        return _parse_order_book(symbol, self._check(data)[0])

    async def fetch_candles(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {"symbol": symbol, "granularity": _TIMEFRAME_MAP.get(timeframe, timeframe), "limit": limit}
        data = await self._http.get("/api/v2/spot/market/candles", params=params)
        return [_parse_candle(k) for k in self._check(data)]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        data = await self._http.get("/api/v2/spot/market/fills", params={"symbol": symbol, "limit": limit})
        return [_parse_trade(t) for t in self._check(data)]

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        path = "/api/v2/spot/account/assets"
        data = await self._http.get(path, headers=self._signed_get(path))
        return _parse_balance(self._check(data), data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        path = "/api/v2/spot/trade/place-order"
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side.lower(),
            "orderType": "limit" if order_type.lower() == "limit" else "market",
            "size": str(amount),
        }
        if order_type.lower() == "limit":
            body["force"] = "gtc"
            if price is not None:
                body["price"] = str(price)
        body_str = json.dumps(body)
        data = await self._http.post(path, data=body, headers=self._signed_post(path, body_str))
        r = self._check(data)
        first = r[0] if r else {}
        return Order(
            id=first.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        path = "/api/v2/spot/trade/cancel-order"
        body = {"symbol": symbol, "orderId": order_id}
        body_str = json.dumps(body)
        data = await self._http.post(path, data=body, headers=self._signed_post(path, body_str))
        r = self._check(data)
        first = r[0] if r else {}
        return Order(id=first.get("orderId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        path = self._path("/api/v2/spot/trade/orderInfo", {"orderId": order_id})
        data = await self._http.get(path, headers=self._signed_get(path))
        r = self._check(data)
        return _parse_order(r[0]) if r else Order(id=order_id, symbol=symbol, side="", type="", amount=0)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        path = self._path("/api/v2/spot/trade/unfilled-orders", {"symbol": symbol} if symbol else None)
        data = await self._http.get(path, headers=self._signed_get(path))
        return [_parse_order(o) for o in self._check(data)]

    # ── Sync ──

    def fetch_ticker_sync(self, symbol: str) -> Ticker:
        data = self._http.sync_get("/api/v2/spot/market/tickers", params={"symbol": symbol})
        return _parse_ticker(self._check(data)[0])

    def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = self._http.sync_get("/api/v2/spot/market/orderbook", params={"symbol": symbol, "limit": limit})
        return _parse_order_book(symbol, self._check(data)[0])

    def fetch_candles_sync(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {"symbol": symbol, "granularity": _TIMEFRAME_MAP.get(timeframe, timeframe), "limit": limit}
        data = self._http.sync_get("/api/v2/spot/market/candles", params=params)
        return [_parse_candle(k) for k in self._check(data)]

    def fetch_balance_sync(self) -> Balance:
        path = "/api/v2/spot/account/assets"
        data = self._http.sync_get(path, headers=self._signed_get(path))
        return _parse_balance(self._check(data), data)

    def create_order_sync(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        path = "/api/v2/spot/trade/place-order"
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side.lower(),
            "orderType": "limit" if order_type.lower() == "limit" else "market",
            "size": str(amount),
        }
        if order_type.lower() == "limit":
            body["force"] = "gtc"
            if price is not None:
                body["price"] = str(price)
        body_str = json.dumps(body)
        data = self._http.sync_post(path, data=body, headers=self._signed_post(path, body_str))
        r = self._check(data)
        first = r[0] if r else {}
        return Order(
            id=first.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    def cancel_order_sync(self, order_id: str, symbol: str) -> Order:
        path = "/api/v2/spot/trade/cancel-order"
        body = {"symbol": symbol, "orderId": order_id}
        body_str = json.dumps(body)
        data = self._http.sync_post(path, data=body, headers=self._signed_post(path, body_str))
        r = self._check(data)
        first = r[0] if r else {}
        return Order(id=first.get("orderId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)


# ── Parsers ──


def _parse_ticker(d: dict[str, Any]) -> Ticker:
    return Ticker(
        symbol=d.get("symbol", ""),
        last=float(d.get("lastPr", 0) or 0),
        bid=float(d.get("bidPr", 0) or 0),
        ask=float(d.get("askPr", 0) or 0),
        high=float(d.get("high24h", 0) or 0),
        low=float(d.get("low24h", 0) or 0),
        volume=float(d.get("baseVolume", 0) or 0),
        quote_volume=float(d.get("quoteVolume", 0) or 0),
        timestamp=int(d.get("ts", 0) or 0),
        raw=d,
    )


def _parse_order_book(symbol: str, d: dict[str, Any]) -> OrderBook:
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(b[0]), amount=float(b[1])) for b in d.get("bids", [])],
        asks=[OrderBookEntry(price=float(a[0]), amount=float(a[1])) for a in d.get("asks", [])],
        timestamp=int(d.get("ts", 0) or 0),
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


def _parse_trade(t: dict[str, Any]) -> Trade:
    return Trade(
        id=str(t.get("tradeId", "")),
        symbol=t.get("symbol", ""),
        side=t.get("side", "").lower(),
        price=float(t.get("price", 0) or 0),
        amount=float(t.get("size", 0) or 0),
        timestamp=int(t.get("ts", 0) or 0),
    )


def _parse_balance(result: list[Any], raw: dict[str, Any]) -> Balance:
    entries = []
    for coin in result:
        free = float(coin.get("available", 0) or 0)
        locked = float(coin.get("frozen", 0) or 0) + float(coin.get("locked", 0) or 0)
        if free > 0 or locked > 0:
            entries.append(BalanceEntry(asset=coin.get("coin", ""), free=free, locked=locked))
    return Balance(assets=entries, raw=raw)


def _parse_order(d: dict[str, Any]) -> Order:
    price = float(d.get("price", 0) or 0)
    return Order(
        id=str(d.get("orderId", "")),
        symbol=d.get("symbol", ""),
        side=d.get("side", "").lower(),
        type=d.get("orderType", "").lower(),
        amount=float(d.get("size", 0) or 0),
        price=price if price > 0 else None,
        filled=float(d.get("baseVolume", 0) or 0),
        status=d.get("status", ""),
        timestamp=int(d.get("cTime", 0) or 0),
        raw=d,
    )
