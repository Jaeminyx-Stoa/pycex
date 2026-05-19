"""HMAC-SHA256 signing utilities for exchange authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode


def hmac_sha256(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def timestamp_ms() -> int:
    return int(time.time() * 1000)


# ── Binance ──


def binance_sign(secret: str, params: dict) -> dict:
    """Add signature to Binance request params."""
    params["timestamp"] = timestamp_ms()
    query = urlencode(params)
    params["signature"] = hmac_sha256(secret, query)
    return params


def binance_headers(api_key: str) -> dict[str, str]:
    return {"X-MBX-APIKEY": api_key}


# ── Bybit ──


def bybit_headers(api_key: str, secret: str, payload: str) -> dict[str, str]:
    """Build Bybit V5 authentication headers."""
    ts = str(timestamp_ms())
    recv_window = "5000"
    sign_str = ts + api_key + recv_window + payload
    return {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-RECV-WINDOW": recv_window,
        "X-BAPI-SIGN": hmac_sha256(secret, sign_str),
    }


# ── OKX ──


def okx_headers(
    api_key: str,
    secret: str,
    passphrase: str,
    method: str,
    path: str,
    body: str = "",
) -> dict[str, str]:
    """Build OKX V5 authentication headers."""
    ts = _okx_timestamp()
    sign_str = ts + method.upper() + path + body
    signature = base64.b64encode(hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()).decode()
    return {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
    }


def _okx_timestamp() -> str:
    t = time.time()
    ms = int(t * 1000) % 1000
    return time.strftime("%Y-%m-%dT%H:%M:%S.", time.gmtime(t)) + f"{ms:03d}Z"
