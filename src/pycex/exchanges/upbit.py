"""Upbit spot exchange adapter — reference implementation for the KRW exchanges.

Upbit has no sandbox/demo environment and is spot-only. Private endpoints are
signed with a JWT (HS256): the payload carries the API access key, a random
nonce, and — when the request has a query (GET/DELETE) or a JSON body that
Upbit treats as a query (POST) — a SHA-512 hash of the urlencoded params as
``query_hash``. See :func:`pycex.auth.upbit_headers`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pycex.auth import upbit_headers
from pycex.base import BaseExchange
from pycex.constants import UPBIT_BASE
from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    NotSupportedError,
    OrderNotFoundError,
    PyCexError,
    RateLimitError,
)
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.market import Market
from pycex.models.mytrade import MyTrade
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade
from pycex.symbols import MarketType, parse_symbol, spot

# Canonical timeframe -> Upbit candle path suffix (`/v1/candles/{suffix}`).
_TF = {"1m": "minutes/1", "5m": "minutes/5", "15m": "minutes/15", "1h": "minutes/60", "4h": "minutes/240", "1d": "days"}
_TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def _iso_utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_to_ms(s: str) -> int:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


class Upbit(BaseExchange):
    """Upbit spot exchange — no sandbox, spot only."""

    name = "upbit"
    candle_page_limit = 200
    supported_timeframes = frozenset({"1m", "5m", "15m", "1h", "4h", "1d"})

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        *,
        sandbox: bool = False,
        market_type: MarketType = "spot",
        timeout: float = 30.0,
    ) -> None:
        if sandbox:
            raise NotSupportedError("upbit has no sandbox environment")
        if market_type != "spot":
            raise NotSupportedError("upbit is spot only")
        self._api_key = api_key
        self._secret = secret
        self.market_type = market_type
        self.sandbox = False
        self._markets: dict[str, Market] = {}
        self._http = HTTPClient(UPBIT_BASE, timeout=timeout, rate=8.0, error_mapper=_map_error)

    def _headers(self, params: dict[str, Any] | None = None) -> dict[str, str]:
        return upbit_headers(self._api_key, self._secret, params)

    # ── Symbols ──

    def to_native(self, symbol: str) -> str:
        s = parse_symbol(symbol)
        return f"{s.quote}-{s.base}"

    def from_native(self, native: str) -> str:
        quote, base = native.split("-", 1)
        return spot(base, quote)

    # ── Market Data ──

    async def fetch_ticker(self, symbol: str) -> Ticker:
        native = self.to_native(symbol)
        data = await self._http.get("/v1/ticker", params={"markets": native})
        return _parse_ticker(data[0])

    async def fetch_order_book(self, symbol: str, *, limit: int = 20) -> OrderBook:
        native = self.to_native(symbol)
        data = await self._http.get("/v1/orderbook", params={"markets": native})
        return _parse_order_book(symbol, data[0], limit)

    async def _fetch_candles_page(
        self, native: str, timeframe: str, *, since: int | None, until: int | None, limit: int
    ) -> list[Candle]:
        params: dict[str, Any] = {"market": native, "count": min(limit, 200)}
        if until is not None:
            params["to"] = _iso_utc(until + 1)  # `to` is exclusive of the given instant
        elif since is not None:
            # Upbit only pages backwards via `to` — anchor the page far enough ahead
            # of `since` that the base class's forward pagination still makes progress.
            params["to"] = _iso_utc(since + limit * _TF_MS[timeframe])
        data = await self._http.get(f"/v1/candles/{_TF[timeframe]}", params=params)
        return sorted((_parse_candle(c) for c in data), key=lambda c: c.timestamp)

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        native = self.to_native(symbol)
        data = await self._http.get("/v1/trades/ticks", params={"market": native, "count": limit})
        return [_parse_trade(symbol, t) for t in data]

    async def fetch_markets(self) -> list[Market]:
        data = await self._http.get("/v1/market/all", params={"is_details": "true"})
        markets = [_parse_market(m) for m in data]
        self._markets = {m.native: m for m in markets}
        return markets

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        data = await self._http.get("/v1/accounts", headers=self._headers())
        return _parse_balance(data)

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        """Place an order.

        Market buys use Upbit's ``ord_type="price"`` — ``amount`` is then the
        **quote-currency total to spend**, not a base-asset quantity. Market
        sells use ``ord_type="market"`` with ``amount`` as the base-asset
        volume, matching every other adapter's convention.
        """
        native = self.to_native(symbol)
        upbit_side = "bid" if side.lower() == "buy" else "ask"
        body: dict[str, Any] = {"market": native, "side": upbit_side}
        if order_type.lower() == "limit":
            if price is None:
                raise InvalidOrderError("limit order requires a price", exchange="upbit")
            body["ord_type"] = "limit"
            body["volume"] = str(amount)
            body["price"] = str(price)
        elif upbit_side == "bid":
            body["ord_type"] = "price"
            body["price"] = str(amount)
        else:
            body["ord_type"] = "market"
            body["volume"] = str(amount)
        data = await self._http.post("/v1/orders", data=body, headers=self._headers(body))
        return _parse_order(symbol, data)

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        params = {"uuid": order_id}
        data = await self._http.delete("/v1/order", params=params, headers=self._headers(params))
        return _parse_order(symbol, data)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        params = {"uuid": order_id}
        data = await self._http.get("/v1/order", params=params, headers=self._headers(params))
        return _parse_order(symbol, data)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        params: dict[str, Any] = {"state": "wait"}
        if symbol is not None:
            params["market"] = self.to_native(symbol)
        data = await self._http.get("/v1/orders", params=params, headers=self._headers(params))
        return [_parse_order(self.from_native(o.get("market", "")), o) for o in data]

    async def fetch_my_trades(
        self, symbol: str | None = None, *, since: int | None = None, limit: int | None = None
    ) -> list[MyTrade]:
        """Upbit has no dedicated fills endpoint — flatten the ``trades`` array of
        completed (``state=done``) orders instead. Per-trade fees are not prorated
        from the order's ``paid_fee``: ``fee`` is always ``0.0`` (see ``raw`` for the
        original trade payload)."""
        params: dict[str, Any] = {"state": "done", "limit": limit or 100}
        if symbol is not None:
            params["market"] = self.to_native(symbol)
        data = await self._http.get("/v1/orders", params=params, headers=self._headers(params))
        trades: list[MyTrade] = []
        for order in data:
            order_symbol = self.from_native(order.get("market", ""))
            quote = order_symbol.split("/")[1]
            order_side = "buy" if order.get("side") == "bid" else "sell"
            created_at = order.get("created_at")
            ts = _parse_iso_to_ms(created_at) if created_at else 0
            for t in order.get("trades", []):
                trades.append(
                    MyTrade(
                        id=str(t.get("uuid", "")),
                        order_id=str(order.get("uuid", "")),
                        symbol=order_symbol,
                        side=order_side,
                        price=float(t.get("price", 0) or 0),
                        amount=float(t.get("volume", 0) or 0),
                        fee=0.0,
                        fee_asset=quote,
                        timestamp=ts,
                        raw=t,
                    )
                )
        if since is not None:
            trades = [t for t in trades if t.timestamp >= since]
        return trades


# ── Errors ──


def _map_error(status: int, data: dict[str, Any]) -> PyCexError | None:
    err = data.get("error") or {}
    name = err.get("name", "")
    message = err.get("message") or "Unknown error"
    if name.startswith("insufficient_funds"):
        return InsufficientBalanceError(message, code=name, exchange="upbit")
    if name in {"invalid_query_payload", "jwt_verification", "expired_access_key", "no_authorization_ip"}:
        return AuthenticationError(message)
    if name == "order_not_found":
        return OrderNotFoundError(message, code=name, exchange="upbit")
    if name == "too_many_requests":
        return RateLimitError(message, code=name, exchange="upbit")
    if name:
        return ExchangeError(message, code=name, exchange="upbit")
    return None


# ── Parsers ──


def _parse_candle(d: dict[str, Any]) -> Candle:
    dt = datetime.fromisoformat(d["candle_date_time_utc"]).replace(tzinfo=timezone.utc)
    return Candle(
        timestamp=int(dt.timestamp() * 1000),
        open=float(d["opening_price"]),
        high=float(d["high_price"]),
        low=float(d["low_price"]),
        close=float(d["trade_price"]),
        volume=float(d["candle_acc_trade_volume"]),
    )


def _parse_market(d: dict[str, Any]) -> Market:
    native = d["market"]
    quote, base = native.split("-", 1)
    market_event = d.get("market_event") or {}
    active = market_event.get("warning") is not True
    return Market(
        symbol=spot(base, quote),
        native=native,
        base=base,
        quote=quote,
        market_type="spot",
        active=active,
        raw=d,
    )


def _parse_ticker(d: dict[str, Any]) -> Ticker:
    quote, base = d["market"].split("-", 1)
    return Ticker(
        symbol=spot(base, quote),
        last=float(d.get("trade_price", 0) or 0),
        bid=0.0,
        ask=0.0,
        high=float(d.get("high_price", 0) or 0),
        low=float(d.get("low_price", 0) or 0),
        volume=float(d.get("acc_trade_volume_24h", d.get("acc_trade_volume", 0)) or 0),
        quote_volume=float(d.get("acc_trade_price_24h", d.get("acc_trade_price", 0)) or 0),
        timestamp=int(d.get("timestamp", 0) or 0),
        raw=d,
    )


def _parse_order_book(symbol: str, d: dict[str, Any], limit: int = 20) -> OrderBook:
    units = d.get("orderbook_units", [])[:limit]
    return OrderBook(
        symbol=symbol,
        bids=[OrderBookEntry(price=float(u["bid_price"]), amount=float(u["bid_size"])) for u in units],
        asks=[OrderBookEntry(price=float(u["ask_price"]), amount=float(u["ask_size"])) for u in units],
        timestamp=int(d.get("timestamp", 0) or 0),
        raw=d,
    )


def _parse_trade(symbol: str, d: dict[str, Any]) -> Trade:
    side = "sell" if d.get("ask_bid") == "ASK" else "buy"
    return Trade(
        id=str(d.get("sequential_id", "")),
        symbol=symbol,
        side=side,
        price=float(d.get("trade_price", 0) or 0),
        amount=float(d.get("trade_volume", 0) or 0),
        timestamp=int(d.get("timestamp", 0) or 0),
    )


def _parse_balance(result: list[Any]) -> Balance:
    entries = []
    for c in result:
        free = float(c.get("balance", 0) or 0)
        locked = float(c.get("locked", 0) or 0)
        if free > 0 or locked > 0:
            entries.append(BalanceEntry(asset=c.get("currency", ""), free=free, locked=locked))
    return Balance(assets=entries, raw={"accounts": result})


def _parse_order(symbol: str, d: dict[str, Any]) -> Order:
    ord_type = d.get("ord_type", "")
    price_raw = d.get("price")
    price = float(price_raw) if price_raw not in (None, "") and ord_type == "limit" else None
    volume_raw = d.get("volume")
    if volume_raw not in (None, ""):
        amount = float(volume_raw)
    elif price_raw not in (None, ""):
        amount = float(price_raw)
    else:
        amount = 0.0
    created_at = d.get("created_at")
    return Order(
        id=str(d.get("uuid", "")),
        symbol=symbol,
        side="buy" if d.get("side") == "bid" else "sell",
        type="market" if ord_type in ("price", "market") else "limit",
        amount=amount,
        price=price,
        filled=float(d.get("executed_volume", 0) or 0),
        status=d.get("state", ""),
        timestamp=_parse_iso_to_ms(created_at) if created_at else 0,
        raw=d,
    )
