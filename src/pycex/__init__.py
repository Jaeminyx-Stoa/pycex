"""pycex — Unified Python wrapper for cryptocurrency exchanges."""

from pycex.base import BaseExchange
from pycex.constants import (
    BINANCE_BASE,
    BINANCE_TESTNET,
    BITGET_BASE,
    BITHUMB_BASE,
    BUY,
    BYBIT_BASE,
    BYBIT_TESTNET,
    KORBIT_BASE,
    LIMIT,
    MARKET,
    OKX_BASE,
    SELL,
    UPBIT_BASE,
)
from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    NetworkError,
    NotSupportedError,
    OrderNotFoundError,
    PyCexError,
    RateLimitError,
    SymbolNotFoundError,
)
from pycex.exchanges import OKX, Binance, Bitget, Bithumb, Bybit, Korbit, Upbit
from pycex.factory import create_exchange
from pycex.models import FundingRate, Market, MyTrade, Position
from pycex.symbols import parse_symbol

__version__ = "0.2.0"
__all__ = [
    "BaseExchange",
    "Binance",
    "Bitget",
    "Bithumb",
    "Bybit",
    "Korbit",
    "OKX",
    "Upbit",
    "BINANCE_BASE",
    "BINANCE_TESTNET",
    "BITGET_BASE",
    "BITHUMB_BASE",
    "BYBIT_BASE",
    "BYBIT_TESTNET",
    "KORBIT_BASE",
    "OKX_BASE",
    "UPBIT_BASE",
    "BUY",
    "SELL",
    "LIMIT",
    "MARKET",
    "PyCexError",
    "AuthenticationError",
    "ExchangeError",
    "RateLimitError",
    "InsufficientBalanceError",
    "InvalidOrderError",
    "OrderNotFoundError",
    "NetworkError",
    "SymbolNotFoundError",
    "NotSupportedError",
    "FundingRate",
    "Market",
    "MyTrade",
    "Position",
    "create_exchange",
    "parse_symbol",
]
