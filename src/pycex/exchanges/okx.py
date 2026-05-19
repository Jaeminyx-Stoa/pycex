"""OKX V5 exchange adapter."""

from __future__ import annotations

import json

from pycex.auth import okx_headers
from pycex.base import BaseExchange
from pycex.constants import OKX_BASE, OKX_BROKER_ID
from pycex.exceptions import ExchangeError
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
    "1h": "1H",
    "4h": "4H",
    "1d": "1D",
    "1w": "1W",
}


class OKX(BaseExchange):
    name = "okx"

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
        if OKX_BROKER_ID:
            broker_headers["broker-id"] = OKX_BROKER_ID
        self._http = HTTPClient(OKX_BASE, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def _check(self, data: dict) -> list:
        code = data.get("code", "0")
        if code != "0":
            raise ExchangeError(data.get("msg", "Unknown error"), code=code, exchange="okx")
        return data.get("data", [])

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        headers = okx_headers(self._api_key, self._secret, self._passphrase, method, path, body)
        if self._demo:
            headers["x-simulated-trading"] = "1"
        return headers

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        data = await self._http.get("/api/v5/market/ticker", params={"instId": symbol})
        result = self._check(data)
        return _parse_ticker(result[0])

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = await self._http.get("/api/v5/market/books", params={"instId": symbol, "sz": limit})
        result = self._check(data)
        return _parse_order_book(symbol, result[0] if result else {})

    async def fetch_candles(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {"instId": symbol, "bar": _TIMEFRAME_MAP.get(timeframe, timeframe), "limit": str(limit)}
        data = await self._http.get("/api/v5/market/candles", params=params)
        result = self._check(data)
        return [_parse_candle(k) for k in result]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        data = await self._http.get("/api/v5/market/trades", params={"instId": symbol, "limit": str(limit)})
        result = self._check(data)
        return [_parse_trade(t) for t in result]

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        path = "/api/v5/account/balance"
        data = await self._http.get(path, headers=self._auth_headers("GET", path))
        result = self._check(data)
        return _parse_balance(result, data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        path = "/api/v5/trade/order"
        body: dict = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side.lower(),
            "ordType": "limit" if order_type.lower() == "limit" else "market",
            "sz": str(amount),
        }
        if OKX_BROKER_ID:
            body["tag"] = OKX_BROKER_ID
        if price is not None:
            body["px"] = str(price)
        body_str = json.dumps(body)
        data = await self._http.post(path, data=body, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        return Order(
            id=r.get("ordId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        path = "/api/v5/trade/cancel-order"
        body = {"instId": symbol, "ordId": order_id}
        body_str = json.dumps(body)
        data = await self._http.post(path, data=body, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        return Order(id=r.get("ordId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        path = f"/api/v5/trade/order?instId={symbol}&ordId={order_id}"
        data = await self._http.get(
            "/api/v5/trade/order",
            params={"instId": symbol, "ordId": order_id},
            headers=self._auth_headers("GET", path),
        )
        result = self._check(data)
        if result:
            return _parse_order(result[0])
        return Order(id=order_id, symbol=symbol, side="", type="", amount=0)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        params: dict = {}
        path = "/api/v5/trade/orders-pending"
        if symbol:
            params["instId"] = symbol
            path += f"?instId={symbol}"
        data = await self._http.get(
            "/api/v5/trade/orders-pending", params=params or None, headers=self._auth_headers("GET", path)
        )
        result = self._check(data)
        return [_parse_order(o) for o in result]

    # ── Sync ──

    def fetch_ticker_sync(self, symbol: str) -> Ticker:
        data = self._http.sync_get("/api/v5/market/ticker", params={"instId": symbol})
        result = self._check(data)
        return _parse_ticker(result[0])

    def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook:
        data = self._http.sync_get("/api/v5/market/books", params={"instId": symbol, "sz": limit})
        result = self._check(data)
        return _parse_order_book(symbol, result[0] if result else {})

    def fetch_balance_sync(self) -> Balance:
        path = "/api/v5/account/balance"
        data = self._http.sync_get(path, headers=self._auth_headers("GET", path))
        result = self._check(data)
        return _parse_balance(result, data)

    def create_order_sync(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        path = "/api/v5/trade/order"
        body: dict = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side.lower(),
            "ordType": "limit" if order_type.lower() == "limit" else "market",
            "sz": str(amount),
        }
        if OKX_BROKER_ID:
            body["tag"] = OKX_BROKER_ID
        if price is not None:
            body["px"] = str(price)
        body_str = json.dumps(body)
        data = self._http.sync_post(path, data=body, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        return Order(
            id=r.get("ordId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    def cancel_order_sync(self, order_id: str, symbol: str) -> Order:
        path = "/api/v5/trade/cancel-order"
        body = {"instId": symbol, "ordId": order_id}
        body_str = json.dumps(body)
        data = self._http.sync_post(path, data=body, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        return Order(id=r.get("ordId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)


# ── Parsers ──


def _parse_ticker(d: dict) -> Ticker:
    return Ticker(
        symbol=d.get("instId", ""),
        last=float(d.get("last", 0)),
        bid=float(d.get("bidPx", 0)),
        ask=float(d.get("askPx", 0)),
        high=float(d.get("high24h", 0)),
        low=float(d.get("low24h", 0)),
        volume=float(d.get("vol24h", 0)),
        quote_volume=float(d.get("volCcy24h", 0)),
        timestamp=int(d.get("ts", 0)),
        raw=d,
    )


def _parse_order_book(symbol: str, d: dict) -> OrderBook:
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(b[0]), amount=float(b[1])) for b in d.get("bids", [])],
        asks=[OrderBookEntry(price=float(a[0]), amount=float(a[1])) for a in d.get("asks", [])],
        timestamp=int(d.get("ts", 0)),
        raw=d,
    )


def _parse_candle(k: list) -> Candle:
    return Candle(
        timestamp=int(k[0]),
        open=float(k[1]),
        high=float(k[2]),
        low=float(k[3]),
        close=float(k[4]),
        volume=float(k[5]),
    )


def _parse_trade(t: dict) -> Trade:
    return Trade(
        id=t.get("tradeId", ""),
        symbol=t.get("instId", ""),
        side=t.get("side", "").lower(),
        price=float(t.get("px", 0)),
        amount=float(t.get("sz", 0)),
        timestamp=int(t.get("ts", 0)),
    )


def _parse_balance(result: list, raw: dict) -> Balance:
    entries = []
    for account in result:
        for detail in account.get("details", []):
            free = float(detail.get("availBal", 0))
            frozen = float(detail.get("frozenBal", 0))
            if free > 0 or frozen > 0:
                entries.append(BalanceEntry(asset=detail["ccy"], free=free, locked=frozen))
    return Balance(assets=entries, raw=raw)


def _parse_order(d: dict) -> Order:
    return Order(
        id=d.get("ordId", ""),
        symbol=d.get("instId", ""),
        side=d.get("side", "").lower(),
        type=d.get("ordType", "").lower(),
        amount=float(d.get("sz", 0)),
        price=float(d["px"]) if d.get("px") and float(d["px"]) > 0 else None,
        filled=float(d.get("accFillSz", 0)),
        status=d.get("state", ""),
        timestamp=int(d.get("cTime", 0)),
        raw=d,
    )
