"""MCP server exposing unified crypto exchange API as tools for AI assistants.

Usage:
    pycex-mcp

    # Claude Desktop config (claude_desktop_config.json)
    {
        "mcpServers": {
            "crypto": {
                "command": "pycex-mcp",
                "env": {
                    "PYCEX_EXCHANGE": "binance",
                    "PYCEX_API_KEY": "your_api_key",
                    "PYCEX_SECRET": "your_secret",
                    "PYCEX_SANDBOX": "false",
                    "PYCEX_MARKET_TYPE": "spot"
                }
            }
        }
    }

Exchange selection and credentials go through the same
``pycex.factory.create_exchange`` the CLI uses — see that module for the
``PYCEX_{EXCHANGE}_API_KEY``/``_SECRET``/``_PASSPHRASE`` per-exchange env var
fallback used when the generic ``PYCEX_API_KEY``/``_SECRET``/``_PASSPHRASE``
below are left unset.
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from pycex.base import BaseExchange
from pycex.factory import EXCHANGES, create_exchange
from pycex.symbols import MarketType

mcp = FastMCP(
    "Crypto Exchange",
    instructions=(
        f"{', '.join(sorted(EXCHANGES))} 거래소의 시세 조회, 잔고 확인, 매수/매도 주문을 수행할 수 있습니다. "
        "환경변수 PYCEX_EXCHANGE, PYCEX_API_KEY, PYCEX_SECRET이 필요합니다 "
        "(OKX/Bitget은 PYCEX_PASSPHRASE도 필요). PYCEX_SANDBOX=true로 샌드박스/데모 모드를, "
        "PYCEX_MARKET_TYPE=linear로 무기한 선물을 선택할 수 있습니다."
    ),
)

_TRUTHY = ("1", "true", "yes")

# Default fan-out set for compare_prices/aggregate_balance — six of the
# seven adapters (bybit excluded by controller ruling); overridable via
# PYCEX_COMPARE_EXCHANGES.
_DEFAULT_COMPARE_EXCHANGES = "binance,okx,bitget,upbit,bithumb,korbit"


def _compare_exchange_names() -> list[str]:
    """Exchanges iterated by ``compare_prices``/``aggregate_balance``,
    controlled by ``PYCEX_COMPARE_EXCHANGES`` (comma-separated, case-
    insensitive). Factored out so both tools — and tests — share one
    source of truth for "which exchanges get iterated"."""
    raw = os.environ.get("PYCEX_COMPARE_EXCHANGES", _DEFAULT_COMPARE_EXCHANGES)
    return [n.strip().lower() for n in raw.split(",") if n.strip()]


def _compare_sandbox_and_market_type() -> tuple[bool, MarketType]:
    """Sandbox/market-type for the multi-exchange tools. Unlike
    ``_get_exchange``, this deliberately does *not* fall back to the
    deprecated ``PYCEX_TESTNET`` — these two tools are new factory-based
    code, not a migrated single-exchange path, so there's no legacy config
    to stay compatible with."""
    sandbox = os.environ.get("PYCEX_SANDBOX", "").lower() in _TRUTHY
    market_type: MarketType = "linear" if os.environ.get("PYCEX_MARKET_TYPE", "").lower() == "linear" else "spot"
    return sandbox, market_type


def _get_exchange() -> BaseExchange:
    """Initialize exchange from env vars, via the shared factory."""
    exchange_name = os.environ.get("PYCEX_EXCHANGE", "binance").lower()
    api_key = os.environ.get("PYCEX_API_KEY", "")
    secret = os.environ.get("PYCEX_SECRET", "")
    passphrase = os.environ.get("PYCEX_PASSPHRASE", "")

    sandbox = os.environ.get("PYCEX_SANDBOX", "").lower() in _TRUTHY
    if not sandbox and os.environ.get("PYCEX_TESTNET", "").lower() in _TRUTHY:
        sandbox = True  # deprecated alias, kept for existing configs

    market_type: MarketType = "linear" if os.environ.get("PYCEX_MARKET_TYPE", "").lower() == "linear" else "spot"

    return create_exchange(
        exchange_name, api_key=api_key, secret=secret, passphrase=passphrase, sandbox=sandbox, market_type=market_type
    )


@mcp.tool()
def get_ticker(symbol: str) -> str:
    """암호화폐 현재가를 조회합니다.

    Args:
        symbol: 거래쌍 (예: "BTCUSDT", "BTC-USDT")
    """
    ex = _get_exchange()
    try:
        ticker = ex.fetch_ticker_sync(symbol)
        return json.dumps(
            {
                "symbol": ticker.symbol,
                "last": ticker.last,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "high": ticker.high,
                "low": ticker.low,
                "volume": ticker.volume,
            },
            ensure_ascii=False,
        )
    finally:
        ex.close_sync()


@mcp.tool()
def get_order_book(symbol: str, limit: int = 10) -> str:
    """호가창(매수/매도 호가)을 조회합니다.

    Args:
        symbol: 거래쌍
        limit: 호가 수
    """
    ex = _get_exchange()
    try:
        ob = ex.fetch_order_book_sync(symbol, limit=limit)
        return json.dumps(
            {
                "symbol": ob.symbol,
                "bids": [{"price": b.price, "amount": b.amount} for b in ob.bids[:limit]],
                "asks": [{"price": a.price, "amount": a.amount} for a in ob.asks[:limit]],
            },
            ensure_ascii=False,
        )
    finally:
        ex.close_sync()


@mcp.tool()
def get_balance() -> str:
    """계좌 잔고를 조회합니다."""
    ex = _get_exchange()
    try:
        bal = ex.fetch_balance_sync()
        return json.dumps(
            {"assets": [{"asset": a.asset, "free": a.free, "locked": a.locked, "total": a.total} for a in bal.assets]},
            ensure_ascii=False,
        )
    finally:
        ex.close_sync()


@mcp.tool()
def place_order(symbol: str, side: str, order_type: str, amount: float, price: float | None = None) -> str:
    """주문을 실행합니다. 실제 주문이므로 주의하세요.

    Args:
        symbol: 거래쌍
        side: "buy" 또는 "sell"
        order_type: "limit" 또는 "market"
        amount: 수량
        price: 가격 (limit 주문 시 필수)
    """
    ex = _get_exchange()
    try:
        order = ex.create_order_sync(symbol, side, order_type, amount, price)
        return json.dumps(
            {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.type,
                "amount": order.amount,
                "price": order.price,
                "status": order.status,
            },
            ensure_ascii=False,
        )
    finally:
        ex.close_sync()


@mcp.tool()
def cancel_order(order_id: str, symbol: str) -> str:
    """주문을 취소합니다.

    Args:
        order_id: 주문 ID
        symbol: 거래쌍
    """
    ex = _get_exchange()
    try:
        order = ex.cancel_order_sync(order_id, symbol)
        return json.dumps({"id": order.id, "symbol": order.symbol, "status": "canceled"}, ensure_ascii=False)
    finally:
        ex.close_sync()


# ── Enhanced: Multi-Exchange Comparison ──


@mcp.tool()
def compare_prices(symbol: str) -> str:
    """여러 거래소의 가격을 동시에 비교합니다. 차익거래 기회도 분석합니다.

    Args:
        symbol: 정규 거래쌍, 예: "BTC/USDT" (원화 거래소는 "BTC/KRW")
    """
    names = _compare_exchange_names()
    sandbox, market_type = _compare_sandbox_and_market_type()

    results: dict[str, Any] = {}
    for name in names:
        try:
            ex = create_exchange(name, sandbox=sandbox, market_type=market_type)
            try:
                ticker = ex.fetch_ticker_sync(symbol)
                results[name] = {"price": ticker.last, "bid": ticker.bid, "ask": ticker.ask, "volume": ticker.volume}
            finally:
                ex.close_sync()
        except Exception as e:
            results[name] = {"error": str(e)}

    prices = {k: v["price"] for k, v in results.items() if "price" in v}
    arb: dict[str, Any] = {}
    if len(prices) >= 2:
        cheapest, _cheapest_price = min(prices.items(), key=lambda kv: kv[1])
        most_expensive, _expensive_price = max(prices.items(), key=lambda kv: kv[1])
        spread_pct = (prices[most_expensive] - prices[cheapest]) / prices[cheapest] * 100
        arb = {
            "buy_on": cheapest,
            "sell_on": most_expensive,
            "spread_pct": round(spread_pct, 4),
            "profitable": spread_pct > 0.1,
        }

    return json.dumps({"symbol": symbol, "exchanges": results, "arbitrage": arb}, ensure_ascii=False)


# ── Enhanced: Chart Analysis ──


@mcp.tool()
def analyze_chart(symbol: str, timeframe: str = "1h", period: int = 50) -> str:
    """차트 기술 분석을 수행합니다. SMA, RSI, 볼린저 밴드, 지지/저항선을 계산합니다.

    Args:
        symbol: 거래쌍
        timeframe: "1m", "5m", "15m", "1h", "4h", "1d"
        period: 캔들 수 (기본 50)
    """
    from pycex.mcp.analysis import bollinger_bands, rsi, sma, support_resistance, volatility

    ex = _get_exchange()
    try:
        candles_data = ex.fetch_candles_sync(symbol, timeframe, limit=period)
        if not candles_data:
            return json.dumps({"error": "No candle data available"})

        current = candles_data[-1].close
        sma_20 = sma(candles_data, 20)
        rsi_val = rsi(candles_data, 14)
        vol = volatility(candles_data)
        bb = bollinger_bands(candles_data, 20)
        sr = support_resistance(candles_data)

        signal = "neutral"
        reasons = []
        if rsi_val is not None:
            if rsi_val > 70:
                signal = "overbought"
                reasons.append(f"RSI {rsi_val:.1f} > 70")
            elif rsi_val < 30:
                signal = "oversold"
                reasons.append(f"RSI {rsi_val:.1f} < 30")
        if sma_20 and current > sma_20[-1]:
            reasons.append("Price above SMA20")
        if sma_20 and current < sma_20[-1]:
            reasons.append("Price below SMA20")
        if bb and current > bb["upper"]:
            reasons.append("Above upper Bollinger Band")
        if bb and current < bb["lower"]:
            reasons.append("Below lower Bollinger Band")

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current,
            "sma_20": round(sma_20[-1], 4) if sma_20 else None,
            "rsi_14": round(rsi_val, 2) if rsi_val else None,
            "volatility": round(vol * 100, 4) if vol else None,
            "bollinger_bands": {k: round(v, 4) for k, v in bb.items()} if bb else None,
            "support": round(sr["support"], 4),
            "resistance": round(sr["resistance"], 4),
            "signal": signal,
            "reasons": reasons,
            "candle_count": len(candles_data),
        }
        return json.dumps(result, ensure_ascii=False)
    finally:
        ex.close_sync()


# ── Enhanced: Aggregate Balance ──


@mcp.tool()
def aggregate_balance() -> str:
    """모든 거래소의 잔고를 통합 조회합니다.

    ``PYCEX_{EXCHANGE}_API_KEY``(예: ``PYCEX_BINANCE_API_KEY``)가 설정된 거래소만
    조회하며, 키가 없는 거래소는 건너뛰고 결과의 ``by_exchange``에 그 사실을
    표시합니다. 조회 대상 목록은 ``PYCEX_COMPARE_EXCHANGES``(콤마 구분, 기본값:
    binance,okx,bitget,upbit,bithumb,korbit)로 제어합니다.
    """
    names = _compare_exchange_names()
    sandbox, market_type = _compare_sandbox_and_market_type()

    all_assets: dict[str, dict[str, Any]] = {}
    exchange_balances: dict[str, Any] = {}

    for name in names:
        env_key = f"PYCEX_{name.upper()}_API_KEY"
        if not os.environ.get(env_key, ""):
            exchange_balances[name] = {"skipped": f"{env_key} not configured"}
            continue
        try:
            ex = create_exchange(name, sandbox=sandbox, market_type=market_type)
            try:
                bal = ex.fetch_balance_sync()
                exchange_balances[name] = [{"asset": a.asset, "free": a.free, "locked": a.locked} for a in bal.assets]
                for a in bal.assets:
                    if a.asset not in all_assets:
                        all_assets[a.asset] = {"total_free": 0, "total_locked": 0, "exchanges": []}
                    all_assets[a.asset]["total_free"] += a.free
                    all_assets[a.asset]["total_locked"] += a.locked
                    all_assets[a.asset]["exchanges"].append({"exchange": name, "free": a.free, "locked": a.locked})
            finally:
                ex.close_sync()
        except Exception as e:
            exchange_balances[name] = {"error": str(e)}

    return json.dumps(
        {
            "aggregated": {
                k: {
                    "total": round(v["total_free"] + v["total_locked"], 8),
                    "free": round(v["total_free"], 8),
                    "locked": round(v["total_locked"], 8),
                    "exchanges": v["exchanges"],
                }
                for k, v in sorted(all_assets.items())
            },
            "by_exchange": exchange_balances,
        },
        ensure_ascii=False,
    )


# ── MCP Prompts ──


@mcp.prompt()
def market_analysis(symbol: str = "BTCUSDT") -> str:
    """시장 분석 프롬프트 — AI가 기술 분석과 가격 비교를 수행합니다."""
    return (
        f"{symbol}에 대해 종합적인 시장 분석을 수행해주세요.\n\n"
        f"1. compare_prices로 거래소별 가격을 비교하세요\n"
        f"2. analyze_chart로 1시간봉, 4시간봉, 일봉 기술 분석을 수행하세요\n"
        f"3. get_order_book으로 매수/매도 압력을 확인하세요\n"
        f"4. 위 데이터를 종합하여 단기/중기 전망과 매매 전략을 제안하세요"
    )


@mcp.prompt()
def portfolio_review() -> str:
    """포트폴리오 리뷰 프롬프트 — 전 거래소 잔고를 분석합니다."""
    return (
        "전체 포트폴리오를 분석해주세요.\n\n"
        "1. aggregate_balance로 전 거래소 잔고를 조회하세요\n"
        "2. 각 보유 자산의 현재가를 get_ticker로 확인하세요\n"
        "3. 포트폴리오 구성 비중, 총 평가액, 리스크 분산도를 분석하세요\n"
        "4. 리밸런싱 제안이 있다면 함께 알려주세요"
    )


@mcp.prompt()
def arbitrage_scan() -> str:
    """차익거래 스캔 프롬프트 — 주요 코인의 거래소 간 가격 차이를 찾습니다."""
    return (
        "주요 암호화폐의 거래소 간 차익거래 기회를 스캔해주세요.\n\n"
        "1. compare_prices로 BTC, ETH, SOL, XRP의 거래소별 가격을 비교하세요\n"
        "2. 스프레드가 0.1% 이상인 기회를 찾으세요\n"
        "3. 각 기회의 예상 수익률과 실행 가능성을 평가하세요\n"
        "4. 수수료와 전송 시간을 고려한 실질 수익률을 계산하세요"
    )


def run_server() -> None:
    """Entry point for pycex-mcp command."""
    mcp.run(transport="stdio")
