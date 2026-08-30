"""OKX V5 exchange adapter."""

from __future__ import annotations

import json
from typing import Any

from pycex.auth import okx_headers
from pycex.base import BaseExchange
from pycex.constants import OKX_BASE, OKX_BROKER_ID
from pycex.exceptions import ExchangeError, NotSupportedError, SymbolNotFoundError
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
        sandbox: bool = False,
        market_type: MarketType = "spot",
        demo: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self.market_type = market_type
        self.sandbox = self._resolve_sandbox(sandbox, None, demo)
        self._markets: dict[str, Market] = {}
        broker_headers: dict[str, str] = {}
        if OKX_BROKER_ID:
            broker_headers["broker-id"] = OKX_BROKER_ID
        self._http = HTTPClient(OKX_BASE, timeout=timeout, rate=10.0, default_headers=broker_headers)

    def to_native(self, symbol: str) -> str:
        sym = parse_symbol(symbol)
        if sym.settle:
            return f"{sym.base}-{sym.quote}-SWAP"
        return f"{sym.base}-{sym.quote}"

    def from_native(self, native: str) -> str:
        if native in self._markets:
            return self._markets[native].symbol
        parts = native.split("-")
        if len(parts) < 2:
            raise SymbolNotFoundError(f"cannot resolve native symbol {native!r} for {self.name}")
        base, quote = parts[0], parts[1]
        if len(parts) >= 3 and parts[2] == "SWAP":
            return f"{base}/{quote}:USDT"
        return f"{base}/{quote}"

    def _check(self, data: dict[str, Any]) -> list[Any]:
        code = data.get("code", "0")
        if code != "0":
            raise ExchangeError(data.get("msg", "Unknown error"), code=code, exchange="okx")
        result: list[Any] = data.get("data", [])
        return result

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        headers = okx_headers(self._api_key, self._secret, self._passphrase, method, path, body)
        if self.sandbox:
            headers["x-simulated-trading"] = "1"
        return headers

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v5/market/ticker", params={"instId": native})
        result = self._check(data)
        return _parse_ticker(symbol, result[0])

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v5/market/books", params={"instId": native, "sz": limit})
        result = self._check(data)
        return _parse_order_book(symbol, result[0] if result else {})

    async def _fetch_candles_page(
        self, native: str, timeframe: str, *, since: int | None, until: int | None, limit: int
    ) -> list[Candle]:
        params: dict[str, Any] = {
            "instId": native,
            "bar": _TIMEFRAME_MAP.get(timeframe, timeframe),
            "limit": str(limit),
        }
        # OKX semantics: after=ts -> records OLDER than ts; before=ts -> records NEWER
        # than ts. The two must never be sent together. When `since` is given we only
        # need a lower bound (`before`); the base class's post-page filtering already
        # trims anything past `until`. When only `until` is given (single-page, no
        # since), we need an upper bound (`after`).
        if since is not None:
            params["before"] = str(since - 1)
        elif until is not None:
            params["after"] = str(until + 1)
        data = await self._http.get("/api/v5/market/candles", params=params)
        result = self._check(data)
        return [_parse_candle(k) for k in result]

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v5/market/trades", params={"instId": native, "limit": str(limit)})
        result = self._check(data)
        return [_parse_trade(symbol, t) for t in result]

    async def fetch_markets(self) -> list[Market]:
        raise NotSupportedError("okx.fetch_markets is not implemented yet")

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
        native = self.to_native(symbol)
        body: dict[str, Any] = {
            "instId": native,
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
        native = self.to_native(symbol)
        body = {"instId": native, "ordId": order_id}
        body_str = json.dumps(body)
        data = await self._http.post(path, data=body, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        return Order(id=r.get("ordId", order_id), symbol=symbol, side="", type="", amount=0, raw=data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        native = self.to_native(symbol)
        path = f"/api/v5/trade/order?instId={native}&ordId={order_id}"
        data = await self._http.get(
            "/api/v5/trade/order",
            params={"instId": native, "ordId": order_id},
            headers=self._auth_headers("GET", path),
        )
        result = self._check(data)
        if result:
            return _parse_order(symbol, result[0])
        return Order(id=order_id, symbol=symbol, side="", type="", amount=0)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        params: dict[str, Any] = {}
        path = "/api/v5/trade/orders-pending"
        native = self.to_native(symbol) if symbol else None
        if native:
            params["instId"] = native
            path += f"?instId={native}"
        data = await self._http.get(
            "/api/v5/trade/orders-pending", params=params or None, headers=self._auth_headers("GET", path)
        )
        result = self._check(data)
        return [_parse_order(self.from_native(o.get("instId", "")), o) for o in result]

    async def fetch_my_trades(
        self, symbol: str | None = None, *, since: int | None = None, limit: int | None = None
    ) -> list[MyTrade]:
        raise NotSupportedError("okx.fetch_my_trades is not implemented yet")


# ── Parsers ──


def _parse_ticker(symbol: str, d: dict[str, Any]) -> Ticker:
    return Ticker(
        symbol=symbol,
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


def _parse_order_book(symbol: str, d: dict[str, Any]) -> OrderBook:
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(b[0]), amount=float(b[1])) for b in d.get("bids", [])],
        asks=[OrderBookEntry(price=float(a[0]), amount=float(a[1])) for a in d.get("asks", [])],
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


def _parse_trade(symbol: str, t: dict[str, Any]) -> Trade:
    return Trade(
        id=t.get("tradeId", ""),
        symbol=symbol,
        side=t.get("side", "").lower(),
        price=float(t.get("px", 0)),
        amount=float(t.get("sz", 0)),
        timestamp=int(t.get("ts", 0)),
    )


def _parse_balance(result: list[Any], raw: dict[str, Any]) -> Balance:
    entries = []
    for account in result:
        for detail in account.get("details", []):
            free = float(detail.get("availBal", 0))
            frozen = float(detail.get("frozenBal", 0))
            if free > 0 or frozen > 0:
                entries.append(BalanceEntry(asset=detail["ccy"], free=free, locked=frozen))
    return Balance(assets=entries, raw=raw)


def _parse_order(symbol: str, d: dict[str, Any]) -> Order:
    return Order(
        id=d.get("ordId", ""),
        symbol=symbol,
        side=d.get("side", "").lower(),
        type=d.get("ordType", "").lower(),
        amount=float(d.get("sz", 0)),
        price=float(d["px"]) if d.get("px") and float(d["px"]) > 0 else None,
        filled=float(d.get("accFillSz", 0)),
        status=d.get("state", ""),
        timestamp=int(d.get("cTime", 0)),
        raw=d,
    )
