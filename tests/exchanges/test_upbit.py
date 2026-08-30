"""Tests for the Upbit spot adapter (reference implementation for KRW exchanges)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from pytest_httpx import HTTPXMock

from pycex.auth import jwt_hs256
from pycex.exceptions import NotSupportedError
from pycex.exchanges.upbit import Upbit, _parse_candle, _parse_market, _parse_ticker
from tests.conftest import load_fixture


def test_symbol_roundtrip() -> None:
    ex = Upbit()
    assert ex.to_native("BTC/KRW") == "KRW-BTC"
    assert ex.from_native("KRW-BTC") == "BTC/KRW"


def test_linear_not_supported() -> None:
    with pytest.raises(NotSupportedError):
        Upbit(market_type="linear")


def test_sandbox_not_supported() -> None:
    with pytest.raises(NotSupportedError):
        Upbit(sandbox=True)


def test_parse_candle_uses_utc_open_time() -> None:
    raw = load_fixture("upbit", "candles_1d")[0]
    c = _parse_candle(raw)
    # candle_date_time_utc "YYYY-MM-DDTHH:MM:SS" → epoch ms; 업비트 timestamp 필드(마지막 체결)는 쓰지 않는다
    expected = int(datetime.fromisoformat(raw["candle_date_time_utc"]).replace(tzinfo=timezone.utc).timestamp() * 1000)
    assert c.timestamp == expected
    assert c.timestamp != raw["timestamp"]
    assert c.open == raw["opening_price"] and c.close == raw["trade_price"]
    assert c.volume == raw["candle_acc_trade_volume"]


def test_parse_market() -> None:
    m = _parse_market(load_fixture("upbit", "markets")[0])
    assert m.native.startswith(("KRW-", "BTC-", "USDT-"))
    assert m.symbol == f"{m.base}/{m.quote}"


def test_parse_ticker() -> None:
    t = _parse_ticker(load_fixture("upbit", "ticker")[0])
    assert t.last > 0


def test_jwt_hs256_shape() -> None:
    tok = jwt_hs256("secret", {"access_key": "k", "nonce": "n"})
    assert tok.count(".") == 2
    hdr = json.loads(base64.urlsafe_b64decode(tok.split(".")[0] + "=="))
    assert hdr == {"alg": "HS256", "typ": "JWT"}


def test_jwt_hs256_signature_matches_known_vector() -> None:
    # Verify against an independently recomputed HMAC-SHA256 over header.payload.
    tok = jwt_hs256("s", {"access_key": "k", "nonce": "n"})
    header_b64, payload_b64, sig_b64 = tok.split(".")
    expected_sig = hmac.new(b"s", f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()
    assert sig_b64 == expected_sig_b64


async def test_candles_page_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=load_fixture("upbit", "candles_1d"))
    ex = Upbit()
    out = await ex._fetch_candles_page("KRW-BTC", "1d", since=None, until=None, limit=3)
    req = httpx_mock.get_request()
    assert req.url.path == "/v1/candles/days" and req.url.params["count"] == "3"
    assert out == sorted(out, key=lambda c: c.timestamp)  # 오름차순으로 뒤집었는가
    await ex.close()
