"""Constants for exchange URLs and rate limits."""

from __future__ import annotations

# ── Binance ──
BINANCE_BASE = "https://api.binance.com"
BINANCE_TESTNET = "https://testnet.binance.vision"

# ── Bybit ──
BYBIT_BASE = "https://api.bybit.com"
BYBIT_TESTNET = "https://api-testnet.bybit.com"

# ── OKX ──
OKX_BASE = "https://www.okx.com"
OKX_DEMO = "https://www.okx.com"  # same host, demo flag in header

# ── Bitget ──
BITGET_BASE = "https://api.bitget.com"  # same host for live and demo, demo via paptrading header

# ── Sides ──
BUY = "buy"
SELL = "sell"

# ── Order types ──
LIMIT = "limit"
MARKET = "market"

# ── Broker / Referral IDs ──
# These are sent with every API request for affiliate attribution.
# Apply at each exchange's broker/partner program to get your own IDs.
BINANCE_BROKER_ID = ""
BYBIT_REFERRAL_CODE = ""
OKX_BROKER_ID = ""
BITGET_BROKER_ID = ""  # X-CHANNEL-API-CODE for API broker rebate

# ── Timeframes ──
TIMEFRAME_1m = "1m"
TIMEFRAME_5m = "5m"
TIMEFRAME_15m = "15m"
TIMEFRAME_1h = "1h"
TIMEFRAME_4h = "4h"
TIMEFRAME_1d = "1d"
TIMEFRAME_1w = "1w"
