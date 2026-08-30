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

# ── Upbit ──
UPBIT_BASE = "https://api.upbit.com"  # no sandbox/demo environment

# ── Bithumb ──
BITHUMB_BASE = "https://api.bithumb.com"  # no sandbox/demo environment; v1/v2 REST paths coexist

# ── Korbit ──
KORBIT_BASE = "https://api.korbit.co.kr"  # no sandbox/demo environment

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

# ── Symbol resolution ──
# Quote-asset suffixes tried (longest-match-first is not required here since
# each candidate is checked in this fixed priority order) when an adapter has
# no markets cache yet to resolve a native symbol back to canonical notation.
QUOTE_SUFFIXES: tuple[str, ...] = ("USDT", "USDC", "BTC", "ETH", "BNB", "FDUSD", "KRW")

# ── Timeframes ──
TIMEFRAME_1m = "1m"
TIMEFRAME_5m = "5m"
TIMEFRAME_15m = "15m"
TIMEFRAME_1h = "1h"
TIMEFRAME_4h = "4h"
TIMEFRAME_1d = "1d"
TIMEFRAME_1w = "1w"
