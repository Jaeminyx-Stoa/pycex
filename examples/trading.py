"""Trading example — testnet buy/sell/cancel with Binance.

WARNING: This example places real orders on the Binance testnet.
Set the following environment variables before running:
    export PYCEX_API_KEY="your_testnet_api_key"
    export PYCEX_SECRET="your_testnet_secret"

Get testnet credentials at: https://testnet.binance.vision/
"""

import os

from pycex import Binance

api_key = os.environ.get("PYCEX_API_KEY", "")
secret = os.environ.get("PYCEX_SECRET", "")

if not api_key or not secret:
    print("Set PYCEX_API_KEY and PYCEX_SECRET environment variables.")
    print("Get testnet credentials at: https://testnet.binance.vision/")
    raise SystemExit(1)

with Binance(api_key=api_key, secret=secret, testnet=True) as ex:
    # Check current balance
    balance = ex.fetch_balance_sync()
    print("Current balance:")
    for asset in balance.assets:
        print(f"  {asset.asset}: free={asset.free:,.8g}, locked={asset.locked:,.8g}")

    # Check a specific asset
    usdt = balance.get("USDT")
    if usdt:
        print(f"\nUSDT available: {usdt.free:,.2f}")

    # Get current BTC price
    ticker = ex.fetch_ticker_sync("BTCUSDT")
    print(f"\nBTC price: ${ticker.last:,.2f}")

    # Place a limit buy order well below market price (so it won't fill)
    buy_price = round(ticker.last * 0.80, 2)  # 20% below market
    print(f"\nPlacing limit buy: 0.001 BTC @ ${buy_price:,.2f}")
    buy_order = ex.create_order_sync("BTCUSDT", "buy", "limit", amount=0.001, price=buy_price)
    print(f"  Order ID: {buy_order.id}")
    print(f"  Status  : {buy_order.status}")
    print(f"  Side    : {buy_order.side}")
    print(f"  Amount  : {buy_order.amount}")
    print(f"  Price   : {buy_order.price}")

    # Place a limit sell order well above market price
    sell_price = round(ticker.last * 1.20, 2)  # 20% above market
    print(f"\nPlacing limit sell: 0.001 BTC @ ${sell_price:,.2f}")
    sell_order = ex.create_order_sync("BTCUSDT", "sell", "limit", amount=0.001, price=sell_price)
    print(f"  Order ID: {sell_order.id}")
    print(f"  Status  : {sell_order.status}")

    # Cancel the buy order
    print(f"\nCanceling buy order {buy_order.id}...")
    canceled = ex.cancel_order_sync(buy_order.id, "BTCUSDT")
    print(f"  Canceled: {canceled.id}")

    # Cancel the sell order
    print(f"Canceling sell order {sell_order.id}...")
    canceled = ex.cancel_order_sync(sell_order.id, "BTCUSDT")
    print(f"  Canceled: {canceled.id}")

    print("\nDone! All test orders placed and canceled.")
