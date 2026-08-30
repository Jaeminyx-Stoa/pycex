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
from pycex.exchanges import OKX, Binance, Bitget, Bithumb, Bybit, Upbit

__version__ = "0.1.0"
__all__ = [
    "BaseExchange",
    "Binance",
    "Bitget",
    "Bithumb",
    "Bybit",
    "OKX",
    "Upbit",
    "BINANCE_BASE",
    "BINANCE_TESTNET",
    "BITGET_BASE",
    "BITHUMB_BASE",
    "BYBIT_BASE",
    "BYBIT_TESTNET",
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
]
