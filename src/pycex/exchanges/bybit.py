"""Bybit V5 exchange adapter."""

from __future__ import annotations

import json
from typing import Any

from pycex.auth import bybit_headers
from pycex.base import BaseExchange
from pycex.constants import BYBIT_BASE, BYBIT_REFERRAL_CODE, BYBIT_TESTNET
from pycex.exceptions import ExchangeError
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade

_TIMEFRAME_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1d": "D",
    "1w": "W",
}

_CATEGORY = "spot"


class Bybit(BaseExchange):
    name = "bybit"

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        *,
        testnet: bool = False,
        timeout: float = 30.0,
        category: str = "spot",
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        self._category = category
        base = BYBIT_TESTNET if testnet else BYBIT_BASE
        broker_headers: dict[str, str] = {}
        if BYBIT_REFERRAL_CODE:
            broker_headers["Referer"] = BYBIT_REFERRAL_CODE
        self._http = HTTPClient(base, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def _check(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("retCode", 0) != 0:
            raise ExchangeError(data.get("retMsg", "Unknown error"), code=data.get("retCode"), exchange="bybit")
        result: dict[str, Any] = data.get("result", data)
        return result

    def _auth_get_headers(self, query: str) -> dict[str, str]:
        return bybit_headers(self._api_key, self._secret, query)

    def _auth_post_headers(self, body: dict[str, Any]) -> dict[str, str]:
        payload = json.dumps(body)
        headers = bybit_headers(self._api_key, self._secret, payload)
        headers["Content-Type"] = "application/json"
        return headers

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        params = {"category": self._category, "symbol": symbol}
        data = await self._http.get("/v5/market/tickers", params=params)
        result = self._check(data)
        return _parse_ticker(result["list[Any]"][0])

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        params = {"category": self._category, "symbol": symbol, "limit": limit}
        data = await self._http.get("/v5/market/orderbook", params=params)
        result = self._check(data)
        return _parse_order_book(symbol, result)

    async def fetch_candles(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {
            "category": self._category,
            "symbol": symbol,
            "interval": _TIMEFRAME_MAP.get(timeframe, timeframe),
            "limit": limit,
        }
        data = await self._http.get("/v5/market/kline", params=params)
        result = self._check(data)
        return [_parse_candle(k) for k in result.get("list[Any]", [])]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        params = {"category": self._category, "symbol": symbol, "limit": limit}
        data = await self._http.get("/v5/market/recent-trade", params=params)
        result = self._check(data)
        return [_parse_trade(t) for t in result.get("list[Any]", [])]

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        query = "accountType=UNIFIED"
        headers = self._auth_get_headers(query)
        data = await self._http.get("/v5/account/wallet-balance", params={"accountType": "UNIFIED"}, headers=headers)
        result = self._check(data)
        return _parse_balance(result, data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        body: dict[str, Any] = {
            "category": self._category,
            "symbol": symbol,
            "side": "Buy" if side.lower() == "buy" else "Sell",
            "orderType": "Limit" if order_type.lower() == "limit" else "Market",
            "qty": str(amount),
        }
        if price is not None:
            body["price"] = str(price)
            body["timeInForce"] = "GTC"
        data = await self._http.post("/v5/order/create", data=body, headers=self._auth_post_headers(body))
        result = self._check(data)
        return Order(
            id=result.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        body = {"category": self._category, "symbol": symbol, "orderId": order_id}
        data = await self._http.post("/v5/order/cancel", data=body, headers=self._auth_post_headers(body))
        result = self._check(data)
        return Order(id=result.get("orderId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        query = f"category={self._category}&symbol={symbol}&orderId={order_id}"
        params = {"category": self._category, "symbol": symbol, "orderId": order_id}
        data = await self._http.get("/v5/order/realtime", params=params, headers=self._auth_get_headers(query))
        result = self._check(data)
        if result.get("list[Any]"):
            return _parse_order(result["list[Any]"][0])
        return Order(id=order_id, symbol=symbol, side="", type="", amount=0)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        params: dict[str, Any] = {"category": self._category}
        if symbol:
            params["symbol"] = symbol
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        data = await self._http.get("/v5/order/realtime", params=params, headers=self._auth_get_headers(query))
        result = self._check(data)
        return [_parse_order(o) for o in result.get("list[Any]", [])]

    # ── Sync ──

    def fetch_ticker_sync(self, symbol: str) -> Ticker:
        params = {"category": self._category, "symbol": symbol}
        data = self._http.sync_get("/v5/market/tickers", params=params)
        result = self._check(data)
        return _parse_ticker(result["list[Any]"][0])

    def fetch_candles_sync(self, symbol: str, timeframe: str = "1h", *, limit: int = 100) -> list[Candle]:
        params = {
            "category": self._category,
            "symbol": symbol,
            "interval": _TIMEFRAME_MAP.get(timeframe, timeframe),
            "limit": limit,
        }
        data = self._http.sync_get("/v5/market/kline", params=params)
        result = self._check(data)
        return [_parse_candle(k) for k in result.get("list[Any]", [])]

    def fetch_order_book_sync(self, symbol: str, *, limit: int = 20) -> OrderBook:
        params = {"category": self._category, "symbol": symbol, "limit": limit}
        data = self._http.sync_get("/v5/market/orderbook", params=params)
        result = self._check(data)
        return _parse_order_book(symbol, result)

    def fetch_balance_sync(self) -> Balance:
        query = "accountType=UNIFIED"
        headers = self._auth_get_headers(query)
        data = self._http.sync_get("/v5/account/wallet-balance", params={"accountType": "UNIFIED"}, headers=headers)
        result = self._check(data)
        return _parse_balance(result, data)

    def create_order_sync(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        body: dict[str, Any] = {
            "category": self._category,
            "symbol": symbol,
            "side": "Buy" if side.lower() == "buy" else "Sell",
            "orderType": "Limit" if order_type.lower() == "limit" else "Market",
            "qty": str(amount),
        }
        if price is not None:
            body["price"] = str(price)
            body["timeInForce"] = "GTC"
        data = self._http.sync_post("/v5/order/create", data=body, headers=self._auth_post_headers(body))
        result = self._check(data)
        return Order(
            id=result.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            type=order_type.lower(),
            amount=amount,
            price=price,
            raw=data,
        )

    def cancel_order_sync(self, order_id: str, symbol: str) -> Order:
        body = {"category": self._category, "symbol": symbol, "orderId": order_id}
        data = self._http.sync_post("/v5/order/cancel", data=body, headers=self._auth_post_headers(body))
        result = self._check(data)
        return Order(id=result.get("orderId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)


# ── Parsers ──


def _parse_ticker(d: dict[str, Any]) -> Ticker:
    return Ticker(
        symbol=d.get("symbol", ""),
        last=float(d.get("lastPrice", 0)),
        bid=float(d.get("bid1Price", 0)),
        ask=float(d.get("ask1Price", 0)),
        high=float(d.get("highPrice24h", 0)),
        low=float(d.get("lowPrice24h", 0)),
        volume=float(d.get("volume24h", 0)),
        quote_volume=float(d.get("turnover24h", 0)),
        raw=d,
    )


def _parse_order_book(symbol: str, d: dict[str, Any]) -> OrderBook:
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(b[0]), amount=float(b[1])) for b in d.get("b", [])],
        asks=[OrderBookEntry(price=float(a[0]), amount=float(a[1])) for a in d.get("a", [])],
        timestamp=int(d.get("ts", 0)),
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
        id=t.get("execId", ""),
        symbol=t.get("symbol", ""),
        side=t.get("side", "").lower(),
        price=float(t.get("price", 0)),
        amount=float(t.get("size", 0)),
        timestamp=int(t.get("time", 0)),
    )


def _parse_balance(result: dict[str, Any], raw: dict[str, Any]) -> Balance:
    entries = []
    for account in result.get("list[Any]", []):
        for coin in account.get("coin", []):
            free = float(coin.get("availableToWithdraw", 0))
            locked = float(coin.get("locked", 0))
            if free > 0 or locked > 0:
                entries.append(BalanceEntry(asset=coin["coin"], free=free, locked=locked))
    return Balance(assets=entries, raw=raw)


def _parse_order(d: dict[str, Any]) -> Order:
    return Order(
        id=d.get("orderId", ""),
        symbol=d.get("symbol", ""),
        side=d.get("side", "").lower(),
        type=d.get("orderType", "").lower(),
        amount=float(d.get("qty", 0)),
        price=float(d["price"]) if d.get("price") and float(d["price"]) > 0 else None,
        filled=float(d.get("cumExecQty", 0)),
        status=d.get("orderStatus", ""),
        timestamp=int(d.get("createdTime", 0)),
        raw=d,
    )
