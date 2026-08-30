"""HMAC-SHA256 signing utilities for exchange authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import urlencode


def hmac_sha256(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def timestamp_ms() -> int:
    return int(time.time() * 1000)


# ── Binance ──


def binance_sign(secret: str, params: dict[str, Any]) -> dict[str, Any]:
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


# ── Bitget ──


def bitget_headers(
    api_key: str,
    secret: str,
    passphrase: str,
    method: str,
    request_path: str,
    body: str = "",
    *,
    demo: bool = False,
) -> dict[str, str]:
    """Build Bitget V2 authentication headers.

    Signature = BASE64(HMAC-SHA256(secret, timestamp + METHOD + requestPath + body)).
    ``request_path`` must include the query string for GET requests. ``demo=True``
    adds the ``paptrading: 1`` header to route to Bitget demo (simulated) trading.
    """
    ts = str(timestamp_ms())
    prehash = ts + method.upper() + request_path + body
    sign = base64.b64encode(hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).digest()).decode()
    headers = {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": passphrase,
        "locale": "en-US",
        "Content-Type": "application/json",
    }
    if demo:
        headers["paptrading"] = "1"
    return headers


# ── Upbit ──


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt_hs256(secret: str, payload: dict[str, Any]) -> str:
    """Encode a minimal HS256 JWT: base64url(header).base64url(payload).base64url(signature)."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def upbit_headers(api_key: str, secret: str, params: dict[str, Any] | None = None) -> dict[str, str]:
    """Build Upbit JWT authentication headers.

    ``params`` is the exact query (or body treated as a query) sent with the
    request; when present its urlencoded form is SHA-512 hashed into
    ``query_hash`` per Upbit's spec. Requests with no params omit the hash.
    """
    payload: dict[str, Any] = {"access_key": api_key, "nonce": str(uuid.uuid4())}
    if params:
        payload["query_hash"] = hashlib.sha512(urlencode(params, doseq=True).encode()).hexdigest()
        payload["query_hash_alg"] = "SHA512"
    return {"Authorization": f"Bearer {jwt_hs256(secret, payload)}"}
