"""OKX V5 exchange adapter — spot (``instType=SPOT``) and USDT-margined linear
perpetual swaps (``instType=SWAP``, ``market_type="linear"``).

Both market types share the same host (``www.okx.com``) and REST surface; only
the ``instType``/``instId`` values and a handful of SWAP-only endpoints
(positions, funding rate) differ, so there is no separate base URL to switch
(unlike Binance's ``fapi.binance.com``).

Doc verification (2026-08-30):
- Live-fetched and confirmed from docs-v5:
  ``GET /api/v5/public/instruments`` — SPOT rows carry ``baseCcy``/``quoteCcy``
  (SWAP rows leave those two empty and carry ``settleCcy``/``ctValCcy``
  instead), plus ``tickSz``, ``lotSz``, ``minSz``, ``state``; confirmed by the
  recorded fixtures ``tests/fixtures/okx/{markets_spot,markets_swap}.json``.
  ``GET /api/v5/trade/fills`` (last-3-days fills) response fields
  (``tradeId, ordId, side, fillPx, fillSz, fee, feeCcy, ts, instId, instType``)
  and params (``instType`` required; ``instId``/``ordId``/``after``/``before``/
  ``limit`` optional — no timestamp-range param on this endpoint, see the note
  on ``fetch_my_trades`` below). ``POST /api/v5/trade/order`` params
  (``instId, tdMode`` [``cash``/``cross``/``isolated``], ``side, ordType, sz,
  px``, ``posSide`` only required in hedge mode).
- The docs-v5 page is one very large single-page app; the fetch tool
  truncated the "Get positions"/"Get funding rate"/"Get candlesticks history"
  sections before their field tables. Those three were instead cross-checked
  against ccxt's ``ts/src/okx.ts`` endpoint table (a well-established,
  independently maintained third-party mapping of OKX's real wire format),
  which confirms the endpoint paths verbatim: ``account/positions``,
  ``public/funding-rate``, ``market/history-candles`` (not
  ``candles-history``/``candlesticks-history`` — two wrong guesses the
  docs-fetch tool produced before this cross-check settled it). Field names
  on those three (``posSide, pos, avgPx, upl, lever, liqPx``;
  ``fundingRate, nextFundingTime``; the candle array shape) match the brief
  and the recorded ``funding``/``candles_swap_1d`` fixtures — the funding
  fixture in particular is a *real* recorded response, so its field names are
  confirmed independently of the docs-fetch truncation — but ccxt's parser
  method bodies were not readable in this pass (same truncation issue on that
  file), so treat those three as fixture/cross-reference-verified rather than
  docs-verified line-by-line.
- Not confirmed in this session: the exact error code OKX returns for a
  hedge-mode ``posSide`` mismatch on ``create_order`` (this adapter never
  sends ``posSide``, i.e. it assumes one-way mode; a hedge-mode account gets
  back whatever ``ExchangeError`` OKX raises, surfaced unchanged — same
  posture as the Binance adapter's ``-4061`` note, but here the code itself
  is not even guessed at).

``fetch_positions``/``fetch_funding_rate`` only work when ``market_type=
"linear"``; on ``"spot"`` they fall through to the shared ``BaseExchange``
default, which raises ``NotSupportedError``.

SWAP order sizing: ``sz`` on SWAP instruments is denominated in **contracts**,
not base-asset quantity (see ``ctVal``/``ctValCcy`` in ``fetch_markets``).
``create_order``/``cancel_order`` do not convert amount<->contracts in this
phase — callers pass ``sz`` directly (contracts) when trading SWAP symbols.

Inverse (coin-margined) perpetuals are out of scope in this phase — only
USDT-settled linear (``settle == quote``) is supported; ``BTC/USD:BTC``-style
canonical symbols or ``*-USD-SWAP`` native symbols raise
``SymbolNotFoundError``.
"""

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import urlencode

from pycex.auth import okx_headers
from pycex.base import BaseExchange
from pycex.constants import OKX_BASE, OKX_BROKER_ID
from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    OrderNotFoundError,
    PyCexError,
    RateLimitError,
    SymbolNotFoundError,
)
from pycex.http import HTTPClient
from pycex.models.balance import Balance, BalanceEntry
from pycex.models.candle import Candle
from pycex.models.funding import FundingRate
from pycex.models.market import Market
from pycex.models.mytrade import MyTrade
from pycex.models.order import Order
from pycex.models.orderbook import OrderBook, OrderBookEntry
from pycex.models.position import Position
from pycex.models.ticker import Ticker
from pycex.models.trade import Trade
from pycex.symbols import MarketType, parse_symbol
from pycex.symbols import linear as make_linear_symbol
from pycex.symbols import spot as make_spot_symbol

# 🚨 Live-verified 2026-08-30: OKX's plain "1D" bar aligns to Hong Kong time
# (UTC+8), NOT UTC midnight — `bar=1D` returns bars 8h offset from
# `bar=1Dutc` for the same instrument (confirmed by diffing the two live:
# 1D gives ts=1788019200000, 1Dutc gives ts=1788048000000, exactly 28_800_000ms
# = 8h apart; re-confirmed against the re-recorded fixture
# tests/fixtures/okx/candles_swap_1d.json, see tests/fixtures/NOTES.md). This
# library's candle contract is UTC-epoch-ms bar-open, so daily bars must
# request the "utc"-suffixed granularity instead of the bare one a naive
# reading of the docs would suggest. "1w" is left as the bare "1W" — it is
# not in BaseExchange.supported_timeframes (this library's timeframe
# contract is 1m/5m/15m/1h/4h/1d only) and its Hong-Kong-time behavior was
# not live-verified in this pass.
_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1H",
    "4h": "4H",
    "1d": "1Dutc",
    "1w": "1W",
}


class OKX(BaseExchange):
    name = "okx"
    # history-candles caps `limit` at 100 (the recent /market/candles endpoint
    # allows up to 300, but pagination must stay within the tighter of the two
    # since either endpoint may serve a given page — see _fetch_candles_page).
    candle_page_limit = 100
    # `before=since` asks for records NEWER than `since` and still serves the newest
    # `limit` of them (live probe 2026-08-30: since = now-400d -> 2026-05-23..2026-08-30).
    # `after` (the upper bound) is the cursor that actually walks the history.
    candle_paging = "backward"

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        passphrase: str = "",
        *,
        sandbox: bool = False,
        market_type: MarketType = "spot",
        td_mode: Literal["cross", "isolated"] = "cross",
        demo: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self.market_type = market_type
        self._td_mode = td_mode
        self._inst_type = "SWAP" if market_type == "linear" else "SPOT"
        self.sandbox = self._resolve_sandbox(sandbox, None, demo)
        self._markets: dict[str, Market] = {}
        broker_headers: dict[str, str] = {}
        if OKX_BROKER_ID:
            broker_headers["broker-id"] = OKX_BROKER_ID
        self._http = HTTPClient(
            OKX_BASE, timeout=timeout, rate=10.0, default_headers=broker_headers, error_mapper=_error_mapper
        )

    def to_native(self, symbol: str) -> str:
        sym = parse_symbol(symbol)
        if sym.settle:
            if sym.settle != sym.quote:
                raise SymbolNotFoundError(
                    f"okx: inverse/cross-settle perpetuals are out of scope (USDT-settled only): {symbol!r}"
                )
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
            if quote == "USD":
                raise SymbolNotFoundError(f"okx: inverse perpetual {native!r} is out of scope (USDT-settled only)")
            return f"{base}/{quote}:{quote}"
        return f"{base}/{quote}"

    def _check(self, data: dict[str, Any]) -> list[Any]:
        code = data.get("code", "0")
        if code != "0":
            raise _map_error(str(code), data.get("msg", "Unknown error"))
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
        # /api/v5/market/history-candles caps `limit` at 100; clamp before either
        # call (the fallback below reuses these same params verbatim) so a page
        # that falls through to history-candles never gets rejected.
        limit = min(limit, 100)
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
        if not result:
            # The regular endpoint only serves a recent rolling window; older
            # ranges come back as an empty `data` array rather than an error.
            # Retry the identical query against history-candles, which covers
            # OKX's full candle history.
            data = await self._http.get("/api/v5/market/history-candles", params=params)
            result = self._check(data)
        candles = [_parse_candle(k) for k in result]
        candles.sort(key=lambda c: c.timestamp)
        return candles

    async def fetch_trades(self, symbol: str, *, limit: int = 100) -> list[Trade]:
        native = self.to_native(symbol)
        data = await self._http.get("/api/v5/market/trades", params={"instId": native, "limit": str(limit)})
        result = self._check(data)
        return [_parse_trade(symbol, t) for t in result]

    async def fetch_markets(self) -> list[Market]:
        data = await self._http.get("/api/v5/public/instruments", params={"instType": self._inst_type})
        result = self._check(data)
        markets = [_parse_market(d, self.market_type) for d in result]
        self._markets = {m.native: m for m in markets}
        return markets

    # ── Account ──

    async def fetch_balance(self) -> Balance:
        path = "/api/v5/account/balance"
        data = await self._http.get(path, headers=self._auth_headers("GET", path))
        result = self._check(data)
        return _parse_balance(result, data)

    async def fetch_positions(self, symbols: list[str] | None = None) -> list[Position]:
        if self.market_type != "linear":
            return await super().fetch_positions(symbols)
        path = "/api/v5/account/positions"
        query = {"instType": "SWAP"}
        full_path = f"{path}?{urlencode(query)}"
        data = await self._http.get(path, params=query, headers=self._auth_headers("GET", full_path))
        result = self._check(data)
        positions = [
            _parse_position(self.from_native(str(p.get("instId", ""))), p)
            for p in result
            if float(p.get("pos", 0) or 0) != 0
        ]
        if symbols is not None:
            wanted = set(symbols)
            positions = [p for p in positions if p.symbol in wanted]
        return positions

    async def fetch_funding_rate(self, symbol: str) -> FundingRate:
        if self.market_type != "linear":
            return await super().fetch_funding_rate(symbol)
        native = self.to_native(symbol)
        data = await self._http.get("/api/v5/public/funding-rate", params={"instId": native})
        result = self._check(data)
        return _parse_funding(symbol, result[0] if result else {})

    # ── Trading ──

    async def create_order(
        self, symbol: str, side: str, order_type: str, amount: float, price: float | None = None
    ) -> Order:
        path = "/api/v5/trade/order"
        native = self.to_native(symbol)
        body: dict[str, Any] = {
            "instId": native,
            # SWAP requires cross/isolated margin mode; SPOT is always "cash".
            "tdMode": self._td_mode if self.market_type == "linear" else "cash",
            "side": side.lower(),
            "ordType": "limit" if order_type.lower() == "limit" else "market",
            "sz": str(amount),
        }
        if OKX_BROKER_ID:
            body["tag"] = OKX_BROKER_ID
        if price is not None:
            body["px"] = str(price)
        # posSide is intentionally omitted: this assumes the SWAP account is in
        # one-way mode (OKX's default). A hedge-mode account requires
        # posSide="long"/"short" on every order — see module docstring.
        body_str = json.dumps(body)
        data = await self._http.post_raw(path, body=body_str, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        _raise_on_scode(r)
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
        data = await self._http.post_raw(path, body=body_str, headers=self._auth_headers("POST", path, body_str))
        result = self._check(data)
        r = result[0] if result else {}
        _raise_on_scode(r)
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
        """Fetch own fills via ``GET /api/v5/trade/fills`` (last 3 days).

        That endpoint's ``after``/``before`` params page over ``billId``, not a
        timestamp, so there is no server-side way to pass ``since`` as a range
        filter here; it is instead applied client-side after parsing.
        """
        path = "/api/v5/trade/fills"
        params: dict[str, Any] = {"instType": self._inst_type}
        if symbol is not None:
            params["instId"] = self.to_native(symbol)
        if limit is not None:
            params["limit"] = str(limit)
        full_path = f"{path}?{urlencode(params)}"
        data = await self._http.get(path, params=params, headers=self._auth_headers("GET", full_path))
        result = self._check(data)
        trades = [
            _parse_my_trade(symbol if symbol is not None else self.from_native(str(t.get("instId", ""))), t)
            for t in result
        ]
        if since is not None:
            trades = [t for t in trades if t.timestamp >= since]
        return trades


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


def _parse_market(d: dict[str, Any], market_type: MarketType) -> Market:
    """Parse one ``GET /api/v5/public/instruments`` row.

    SPOT rows carry ``baseCcy``/``quoteCcy`` directly; SWAP rows leave those
    two empty and instead carry ``ctValCcy`` (contract value currency, the
    base) and ``settleCcy`` (settlement/margin currency, the quote/settle for
    a USDT-margined linear contract). ``minSz`` is a quantity floor, not a
    notional one, so ``min_notional`` is always ``None`` for OKX.
    """
    native = str(d.get("instId", ""))
    if market_type == "linear":
        parts = native.split("-")
        base = str(d.get("ctValCcy") or (parts[0] if parts else ""))
        quote = str(d.get("settleCcy") or (parts[1] if len(parts) > 1 else ""))
        symbol = make_linear_symbol(base, quote, quote)
    else:
        base = str(d.get("baseCcy", ""))
        quote = str(d.get("quoteCcy", ""))
        symbol = make_spot_symbol(base, quote)
    tick_sz = d.get("tickSz")
    lot_sz = d.get("lotSz")
    return Market(
        symbol=symbol,
        native=native,
        base=base,
        quote=quote,
        market_type=market_type,
        price_tick=float(tick_sz) if tick_sz not in (None, "") else None,
        amount_step=float(lot_sz) if lot_sz not in (None, "") else None,
        min_notional=None,
        active=d.get("state") == "live",
        raw=d,
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


def _none_if_zero(v: Any) -> float | None:
    """``0``/``""``/missing all mean "not meaningful" (e.g. ``liqPx`` is ``"0"``
    when OKX can't compute a liquidation price for a low-leverage position) —
    same treatment as ``_parse_order``'s ``price`` field."""
    if v in (None, ""):
        return None
    f = float(v)
    return f if f != 0 else None


def _parse_position(symbol: str, d: dict[str, Any]) -> Position:
    pos = float(d.get("pos", 0) or 0)
    pos_side = d.get("posSide", "net")
    side = ("long" if pos > 0 else "short") if pos_side == "net" else pos_side
    return Position(
        symbol=symbol,
        side=side,
        amount=abs(pos),
        entry_price=_none_if_zero(d.get("avgPx")),
        unrealized_pnl=float(d.get("upl", 0) or 0),
        leverage=_none_if_zero(d.get("lever")),
        liquidation_price=_none_if_zero(d.get("liqPx")),
        timestamp=int(d.get("uTime", 0) or d.get("cTime", 0) or 0),
        raw=d,
    )


def _parse_funding(symbol: str, d: dict[str, Any]) -> FundingRate:
    return FundingRate(
        symbol=symbol,
        rate=float(d.get("fundingRate", 0) or 0),
        interval_hours=8,
        next_funding_time=int(d.get("nextFundingTime", 0) or 0),
        timestamp=int(d.get("ts", 0) or 0),
        raw=d,
    )


def _parse_my_trade(symbol: str, t: dict[str, Any]) -> MyTrade:
    return MyTrade(
        id=str(t.get("tradeId", "")),
        order_id=str(t.get("ordId", "")),
        symbol=symbol,
        side=str(t.get("side", "")).lower(),
        price=float(t.get("fillPx", 0) or 0),
        amount=float(t.get("fillSz", 0) or 0),
        fee=float(t.get("fee", 0) or 0),
        fee_asset=str(t.get("feeCcy", "") or ""),
        timestamp=int(t.get("ts", 0) or 0),
        raw=t,
    )


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


# ── Errors ──


def _map_error(code: str, msg: str) -> PyCexError:
    """Map OKX's ``code``/``msg`` pair (present both on HTTP>=400 bodies and on
    HTTP 200 responses with ``code != "0"``) to a ``PyCexError``."""
    if code == "51008":
        return InsufficientBalanceError(msg, code=code, exchange="okx")
    if code in ("50111", "50113", "50114"):
        return AuthenticationError(msg)
    if code == "51603":
        return OrderNotFoundError(msg, code=code, exchange="okx")
    if code == "50011":
        return RateLimitError(msg, code=code, exchange="okx")
    return ExchangeError(msg, code=code, exchange="okx")


def _error_mapper(status: int, data: dict[str, Any]) -> PyCexError | None:
    code = data.get("code")
    if code is None:
        return None
    return _map_error(str(code), str(data.get("msg", "Unknown error")))


def _raise_on_scode(item: dict[str, Any]) -> None:
    """Order/cancel rejections on OKX arrive as HTTP 200 + top-level ``code ==
    "0"`` (which ``_check`` treats as success) with the actual per-item
    rejection in ``data[0].sCode``/``sMsg`` instead — a batch endpoint shape
    where one order in the array can fail while others succeed. Reuses
    ``_map_error`` for the same code table (``51008`` -> insufficient balance,
    ``51603`` -> order not found, etc.)."""
    s_code = str(item.get("sCode", "0"))
    if s_code != "0":
        raise _map_error(s_code, item.get("sMsg", "Unknown error"))
