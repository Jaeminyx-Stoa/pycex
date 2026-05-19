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
            {
                "assets": [
                    {"asset": a.asset, "free": a.free, "locked": a.locked, "total": a.total}
                    for a in bal.assets
                ]
            },
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


def run_server() -> None:
    """Entry point for pycex-mcp command."""
    mcp.run(transport="stdio")
