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
                    "PYCEX_SECRET": "your_secret"
                }
            }
        }
    }
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from pycex.base import BaseExchange

mcp = FastMCP(
    "Crypto Exchange",
    instructions=(
        "Binance, Bybit, OKX 거래소의 시세 조회, 잔고 확인, 매수/매도 주문을 수행할 수 있습니다. "
        "환경변수 PYCEX_EXCHANGE, PYCEX_API_KEY, PYCEX_SECRET이 필요합니다."
    ),
)


def _get_exchange() -> BaseExchange:
    """Initialize exchange from env vars."""
    from pycex import OKX, Binance, Bybit

    exchange_name = os.environ.get("PYCEX_EXCHANGE", "binance").lower()
    api_key = os.environ.get("PYCEX_API_KEY", "")
    secret = os.environ.get("PYCEX_SECRET", "")
    testnet = os.environ.get("PYCEX_TESTNET", "").lower() in ("1", "true", "yes")

    if exchange_name == "binance":
        return Binance(api_key=api_key, secret=secret, testnet=testnet)
    elif exchange_name == "bybit":
        return Bybit(api_key=api_key, secret=secret, testnet=testnet)
    elif exchange_name == "okx":
        passphrase = os.environ.get("PYCEX_PASSPHRASE", "")
        return OKX(api_key=api_key, secret=secret, passphrase=passphrase, demo=testnet)
    else:
        raise ValueError(f"Unknown exchange: {exchange_name}. Use binance, bybit, or okx.")


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
        symbol: 거래쌍 (Binance/Bybit: "BTCUSDT", OKX: "BTC-USDT")
    """
    from pycex import OKX, Binance, Bybit

    testnet = os.environ.get("PYCEX_TESTNET", "").lower() in ("1", "true", "yes")
    okx_symbol = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol
    spot_symbol = symbol.replace("-", "") if "-" in symbol else symbol

    results: dict[str, Any] = {}
    for name, cls, sym in [
        ("binance", Binance, spot_symbol),
        ("bybit", Bybit, spot_symbol),
        ("okx", OKX, okx_symbol),
    ]:
        try:
            ex = cls(testnet=testnet) if name != "okx" else cls(demo=testnet)
            ticker = ex.fetch_ticker_sync(sym)
            results[name] = {"price": ticker.last, "bid": ticker.bid, "ask": ticker.ask, "volume": ticker.volume}
            ex.close_sync()
        except Exception as e:
            results[name] = {"error": str(e)}

    prices = {k: v["price"] for k, v in results.items() if "price" in v}
    arb: dict[str, Any] = {}
    if len(prices) >= 2:
        cheapest = min(prices, key=prices.get)  # type: ignore[arg-type]
        most_expensive = max(prices, key=prices.get)  # type: ignore[arg-type]
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
    """모든 거래소의 잔고를 통합 조회합니다. 각 거래소별 API 키가 환경변수에 설정되어 있어야 합니다.

    환경변수: BINANCE_API_KEY/SECRET, BYBIT_API_KEY/SECRET, OKX_API_KEY/SECRET/PASSPHRASE
    """
    from pycex import OKX, Binance, Bybit

    testnet = os.environ.get("PYCEX_TESTNET", "").lower() in ("1", "true", "yes")
    exchanges_config = [
        (
            "binance",
            Binance,
            {
                "api_key": os.environ.get("BINANCE_API_KEY", os.environ.get("PYCEX_API_KEY", "")),
                "secret": os.environ.get("BINANCE_SECRET", os.environ.get("PYCEX_SECRET", "")),
                "testnet": testnet,
            },
        ),
        (
            "bybit",
            Bybit,
            {
                "api_key": os.environ.get("BYBIT_API_KEY", ""),
                "secret": os.environ.get("BYBIT_SECRET", ""),
                "testnet": testnet,
            },
        ),
        (
            "okx",
            OKX,
            {
                "api_key": os.environ.get("OKX_API_KEY", ""),
                "secret": os.environ.get("OKX_SECRET", ""),
                "passphrase": os.environ.get("OKX_PASSPHRASE", ""),
                "demo": testnet,
            },
        ),
    ]

    all_assets: dict[str, dict[str, Any]] = {}
    exchange_balances: dict[str, Any] = {}

    for name, cls, kwargs in exchanges_config:
        if not kwargs.get("api_key"):
            continue
        try:
            ex = cls(**kwargs)
            bal = ex.fetch_balance_sync()
            exchange_balances[name] = [{"asset": a.asset, "free": a.free, "locked": a.locked} for a in bal.assets]
            for a in bal.assets:
                if a.asset not in all_assets:
                    all_assets[a.asset] = {"total_free": 0, "total_locked": 0, "exchanges": []}
                all_assets[a.asset]["total_free"] += a.free
                all_assets[a.asset]["total_locked"] += a.locked
                all_assets[a.asset]["exchanges"].append({"exchange": name, "free": a.free, "locked": a.locked})
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
