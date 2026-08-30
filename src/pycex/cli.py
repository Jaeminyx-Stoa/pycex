"""CLI tool for pycex."""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

from pycex.base import BaseExchange
from pycex.exceptions import PyCexError
from pycex.factory import EXCHANGES, create_exchange
from pycex.symbols import MarketType


def _make_exchange(args: argparse.Namespace) -> BaseExchange:
    exchange_name = args.exchange or os.environ.get("PYCEX_EXCHANGE", "binance")
    api_key = args.api_key or os.environ.get("PYCEX_API_KEY", "")
    secret = args.secret or os.environ.get("PYCEX_SECRET", "")
    passphrase = os.environ.get("PYCEX_PASSPHRASE", "")

    sandbox = bool(getattr(args, "sandbox", False))
    if getattr(args, "testnet", False):
        warnings.warn("--testnet is deprecated; use --sandbox", DeprecationWarning, stacklevel=2)
        sandbox = True
    market_type_raw = getattr(args, "market_type", None) or "spot"
    market_type: MarketType = "linear" if market_type_raw == "linear" else "spot"

    try:
        return create_exchange(
            exchange_name,
            api_key=api_key,
            secret=secret,
            passphrase=passphrase,
            sandbox=sandbox,
            market_type=market_type,
        )
    except (ValueError, PyCexError) as e:
        # ValueError: unknown exchange name (raised by create_exchange itself).
        # PyCexError: an adapter's own constructor rejecting the combination,
        # e.g. NotSupportedError("upbit has no sandbox environment") — both
        # are user input errors, not bugs, so exit clean with the message
        # instead of a traceback.
        print(str(e), file=sys.stderr)
        sys.exit(1)


def _format(data: object, as_json: bool) -> str:
    if as_json:
        return json.dumps(data, ensure_ascii=False, default=str, indent=2)
    return str(data)


def cmd_ticker(args: argparse.Namespace) -> None:
    ex = _make_exchange(args)
    try:
        t = ex.fetch_ticker_sync(args.symbol)
        if args.json:
            print(json.dumps(t.model_dump(), ensure_ascii=False, indent=2))
        else:
            print(f"{t.symbol}")
            print(f"  Last: {t.last:,.8g}  Bid: {t.bid:,.8g}  Ask: {t.ask:,.8g}")
            print(f"  High: {t.high:,.8g}  Low: {t.low:,.8g}")
            print(f"  Volume: {t.volume:,.2f}")
    finally:
        ex.close_sync()


def cmd_orderbook(args: argparse.Namespace) -> None:
    ex = _make_exchange(args)
    try:
        ob = ex.fetch_order_book_sync(args.symbol, limit=10)
        if args.json:
            print(json.dumps(ob.model_dump(), ensure_ascii=False, indent=2))
        else:
            print(f"Order Book: {ob.symbol}")
            print("  ASK")
            for a in reversed(ob.asks[:5]):
                print(f"    {a.price:>14,.8g}  {a.amount:>14,.8g}")
            print("  ---")
            for b in ob.bids[:5]:
                print(f"    {b.price:>14,.8g}  {b.amount:>14,.8g}")
            print("  BID")
    finally:
        ex.close_sync()


def cmd_balance(args: argparse.Namespace) -> None:
    ex = _make_exchange(args)
    try:
        bal = ex.fetch_balance_sync()
        if args.json:
            print(json.dumps(bal.model_dump(), ensure_ascii=False, indent=2))
        else:
            print("Balance:")
            for a in bal.assets:
                print(f"  {a.asset:>8s}: free={a.free:,.8g}  locked={a.locked:,.8g}  total={a.total:,.8g}")
    finally:
        ex.close_sync()


def cmd_buy(args: argparse.Namespace) -> None:
    ex = _make_exchange(args)
    try:
        order = ex.create_order_sync(args.symbol, "buy", "limit", args.amount, args.price)
        if args.json:
            print(json.dumps(order.model_dump(), ensure_ascii=False, indent=2))
        else:
            print(f"Buy order placed: id={order.id}, {order.symbol}, amount={order.amount}, price={order.price}")
    finally:
        ex.close_sync()


def cmd_sell(args: argparse.Namespace) -> None:
    ex = _make_exchange(args)
    try:
        order = ex.create_order_sync(args.symbol, "sell", "limit", args.amount, args.price)
        if args.json:
            print(json.dumps(order.model_dump(), ensure_ascii=False, indent=2))
        else:
            print(f"Sell order placed: id={order.id}, {order.symbol}, amount={order.amount}, price={order.price}")
    finally:
        ex.close_sync()


def main() -> None:
    parser = argparse.ArgumentParser(prog="pycex", description="Unified crypto exchange CLI")
    parser.add_argument("--exchange", "-e", help=f"Exchange: {', '.join(sorted(EXCHANGES))}")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--secret", help="API secret")
    parser.add_argument("--sandbox", action="store_true", help="Use sandbox/testnet/demo mode")
    parser.add_argument("--testnet", action="store_true", help="[deprecated] use --sandbox instead")
    parser.add_argument(
        "--market-type", dest="market_type", choices=["spot", "linear"], default="spot", help="Market type"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")

    sub = parser.add_subparsers(dest="command")

    p_ticker = sub.add_parser("ticker", help="Get ticker")
    p_ticker.add_argument("symbol", help="Canonical pair, BASE/QUOTE or BASE/QUOTE:SETTLE (e.g. BTC/USDT)")
    p_ticker.set_defaults(func=cmd_ticker)

    p_ob = sub.add_parser("orderbook", help="Get order book")
    p_ob.add_argument("symbol")
    p_ob.set_defaults(func=cmd_orderbook)

    p_bal = sub.add_parser("balance", help="Get balance")
    p_bal.set_defaults(func=cmd_balance)

    p_buy = sub.add_parser("buy", help="Place buy order")
    p_buy.add_argument("symbol")
    p_buy.add_argument("amount", type=float)
    p_buy.add_argument("price", type=float)
    p_buy.set_defaults(func=cmd_buy)

    p_sell = sub.add_parser("sell", help="Place sell order")
    p_sell.add_argument("symbol")
    p_sell.add_argument("amount", type=float)
    p_sell.add_argument("price", type=float)
    p_sell.set_defaults(func=cmd_sell)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)
