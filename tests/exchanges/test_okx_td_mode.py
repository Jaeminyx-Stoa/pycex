"""A-3 — 현물 ``tdMode`` 는 **acctLv 실측**으로 정한다. 모르면 주문하지 않는다.

🚨 실측 2026-09-10(runs/20260910-000749): ``tdMode`` 를 ``"cash"`` 로 **고정**해
두었더니 acctLv=3(Multi-currency margin) 실계좌에서 현물 주문이 전량
``51000 Parameter tdMode error`` 로 거절됐다 — 하네스 2단계 1차 S1·S2·S3·S9 전멸.
OKX 는 acctLv 1(Simple)·2(Single-currency margin) 에서만 ``cash`` 를 받고,
3(Multi-currency)·4(Portfolio) 에서는 ``cross`` 를 요구한다.

그래서 이 어댑터는 **추측하지 않는다**: 계좌 등급을 ``GET /api/v5/account/config``
로 한 번 실측해 캐시하고, 등급을 알 수 없으면 주문을 **보내지 않고** 죽는다.
"""

from __future__ import annotations

import json as json_lib

import pytest
from pytest_httpx import HTTPXMock

from pycex.exceptions import ExchangeError, PyCexError
from pycex.exchanges.okx import OKX

_ORDER_ACK = {"code": "0", "msg": "", "data": [{"ordId": "1", "sCode": "0"}]}


def _config(level: str | None) -> dict:
    row: dict = {"posMode": "net_mode", "perm": "read_only,trade"}
    if level is not None:
        row["acctLv"] = level
    return {"code": "0", "msg": "", "data": [row]}


def _spot() -> OKX:
    return OKX(api_key="k", secret="s", passphrase="p")


def _order_bodies(httpx_mock: HTTPXMock) -> list[dict]:
    return [
        json_lib.loads(r.content.decode())
        for r in httpx_mock.get_requests()
        if r.url.path == "/api/v5/trade/order"
    ]


@pytest.mark.parametrize(("level", "expected"), [("1", "cash"), ("2", "cash"), ("3", "cross"), ("4", "cross")])
async def test_spot_td_mode_follows_measured_account_level(
    httpx_mock: HTTPXMock, level: str, expected: str
) -> None:
    httpx_mock.add_response(json=_config(level))
    httpx_mock.add_response(json=_ORDER_ACK)
    ex = _spot()
    await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    assert _order_bodies(httpx_mock)[0]["tdMode"] == expected
    assert ex.account_level == level
    await ex.close()


async def test_account_level_is_measured_once_and_cached(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_config("3"))
    httpx_mock.add_response(json=_ORDER_ACK, is_reusable=True)
    ex = _spot()
    await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    await ex.create_order("BTC/USDT", "sell", "limit", 0.001, 50000.0)
    configs = [r for r in httpx_mock.get_requests() if r.url.path == "/api/v5/account/config"]
    assert len(configs) == 1
    assert [b["tdMode"] for b in _order_bodies(httpx_mock)] == ["cross", "cross"]
    await ex.close()


async def test_fetch_account_config_returns_the_row(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_config("3"))
    ex = _spot()
    row = await ex.fetch_account_config()
    assert row["acctLv"] == "3"
    assert row["posMode"] == "net_mode"
    assert ex.account_level == "3"
    await ex.close()


# ── 우회 시도: «모르면 cash 로 가정» 을 되살리려는 모든 길을 막는다 ──


@pytest.mark.parametrize("level", [None, "", "9", "unknown"])
async def test_unknown_account_level_never_sends_an_order(httpx_mock: HTTPXMock, level: str | None) -> None:
    """우회 1 — 등급이 비었거나 처음 보는 값이면 **주문 자체가 나가지 않는다.**"""
    httpx_mock.add_response(json=_config(level))
    ex = _spot()
    with pytest.raises(ExchangeError, match="acctLv"):
        await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    assert _order_bodies(httpx_mock) == []
    await ex.close()


async def test_account_config_failure_blocks_the_order(httpx_mock: HTTPXMock) -> None:
    """우회 2 — 등급 조회가 실패하면 «그럼 cash 로» 가 아니라 **fail-closed**."""
    httpx_mock.add_response(json={"code": "50111", "msg": "Invalid OK-ACCESS-KEY", "data": []})
    ex = _spot()
    with pytest.raises(PyCexError):
        await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    assert _order_bodies(httpx_mock) == []
    await ex.close()


async def test_ctor_td_mode_does_not_leak_into_spot(httpx_mock: HTTPXMock) -> None:
    """우회 3 — 생성자 ``td_mode`` 는 무기한 전용이다. 현물 등급 판정을 덮어쓰지 못한다."""
    httpx_mock.add_response(json=_config("1"))
    httpx_mock.add_response(json=_ORDER_ACK)
    ex = OKX(api_key="k", secret="s", passphrase="p", td_mode="isolated")
    await ex.create_order("BTC/USDT", "buy", "limit", 0.001, 50000.0)
    assert _order_bodies(httpx_mock)[0]["tdMode"] == "cash"
    await ex.close()


async def test_account_level_is_not_settable_by_the_caller() -> None:
    """우회 4 — 계좌 등급은 «내가 안다»고 선언할 수 있는 값이 아니다(실측 전용)."""
    ex = _spot()
    with pytest.raises(AttributeError):
        ex.account_level = "1"  # type: ignore[misc]
    await ex.close()


async def test_linear_order_does_not_measure_account_level(httpx_mock: HTTPXMock) -> None:
    """우회 5 — 무기한은 생성자 마진모드를 쓴다. 쓸데없는 계좌 조회를 붙이지 않는다."""
    httpx_mock.add_response(json=_ORDER_ACK)
    ex = OKX(api_key="k", secret="s", passphrase="p", market_type="linear", td_mode="isolated")
    await ex.create_order("BTC/USDT:USDT", "buy", "market", 1)
    assert [r.url.path for r in httpx_mock.get_requests()] == ["/api/v5/trade/order"]
    assert _order_bodies(httpx_mock)[0]["tdMode"] == "isolated"
    await ex.close()
