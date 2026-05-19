"""CLI tool for pycex."""

from __future__ import annotations

import argparse
import json
import os
import sys

from pycex.base import BaseExchange


def _make_exchange(args: argparse.Namespace) -> BaseExchange:
    from pycex import OKX, Binance, Bybit

    exchange_name = args.exchange or os.environ.get("PYCEX_EXCHANGE", "binance")
    api_key = args.api_key or os.environ.get("PYCEX_API_KEY", "")
    secret = args.secret or os.environ.get("PYCEX_SECRET", "")
    testnet = args.testnet

    exchange_name = exchange_name.lower()
    if exchange_name == "binance":
        return Binance(api_key=api_key, secret=secret, testnet=testnet)
    elif exchange_name == "bybit":
        return Bybit(api_key=api_key, secret=secret, testnet=testnet)
    elif exchange_name == "okx":
        passphrase = os.environ.get("PYCEX_PASSPHRASE", "")
        return OKX(api_key=api_key, secret=secret, passphrase=passphrase, demo=testnet)
    else:
        print(f"Unknown exchange: {exchange_name}", file=sys.stderr)
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
    parser.add_argument("--exchange", "-e", help="Exchange: binance, bybit, okx")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--secret", help="API secret")
    parser.add_argument("--testnet", action="store_true", help="Use testnet")
    parser.add_argument("--json", action="store_true", help="JSON output")

    sub = parser.add_subparsers(dest="command")

    p_ticker = sub.add_parser("ticker", help="Get ticker")
    p_ticker.add_argument("symbol", help="Trading pair (e.g., BTCUSDT)")
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
