"""pycex — Unified Python wrapper for cryptocurrency exchanges."""

from pycex.base import BaseExchange
from pycex.constants import (
    BINANCE_BASE,
    BINANCE_TESTNET,
    BITGET_BASE,
    BUY,
    BYBIT_BASE,
    BYBIT_TESTNET,
    LIMIT,
    MARKET,
    OKX_BASE,
    SELL,
)
from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    NetworkError,
    OrderNotFoundError,
    PyCexError,
    RateLimitError,
    SymbolNotFoundError,
)
from pycex.exchanges import OKX, Binance, Bitget, Bybit

__version__ = "0.1.0"
__all__ = [
    "BaseExchange",
    "Binance",
    "Bitget",
    "Bybit",
    "OKX",
    "BINANCE_BASE",
    "BINANCE_TESTNET",
    "BITGET_BASE",
    "BYBIT_BASE",
    "BYBIT_TESTNET",
    "OKX_BASE",
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
]
