"""A-2 — ``create_order`` 가 ``client_order_id``(OKX ``clOrdId``)를 받는다.

없으면 **거래소 수준 멱등이 불가능**하다. 하네스는 자체 생성으로 때웠다
(``w11-okx-live/okxlive/client.py:291``). SDK 는 **받아서 그대로 보내기만**
하고, 값을 스스로 만들어내지 않는다 — 멱등 키의 주인은 호출자다.

OKX 제약: ``clOrdId`` 는 영숫자 1~32자. 어기면 거래소가 아니라 **여기서**
막는다(네트워크로 나가기 전에).
"""

from __future__ import annotations

import json as json_lib

import pytest
from pytest_httpx import HTTPXMock

from pycex.exceptions import ExchangeError, InvalidOrderError
from pycex.exchanges.okx import OKX, _parse_order

_ACK = {"code": "0", "msg": "", "data": [{"ordId": "o1", "clOrdId": "q7abc", "sCode": "0", "sMsg": "Order placed"}]}


def _swap() -> OKX:
    return OKX(api_key="k", secret="s", passphrase="p", market_type="linear")


async def test_client_order_id_is_sent_verbatim(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_ACK)
    ex = _swap()
    order = await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0, client_order_id="q7abc")
    body = json_lib.loads(httpx_mock.get_requests()[-1].content.decode())
    assert body["clOrdId"] == "q7abc"
    assert order.client_order_id == "q7abc"
    await ex.close()


async def test_client_order_id_absent_means_no_key(httpx_mock: HTTPXMock) -> None:
    """SDK 는 멱등 키를 **만들어내지 않는다** — 정책은 호출자(P-1) 몫이다."""
    httpx_mock.add_response(json={"code": "0", "msg": "", "data": [{"ordId": "o1", "sCode": "0"}]})
    ex = _swap()
    order = await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0)
    body = json_lib.loads(httpx_mock.get_requests()[-1].content.decode())
    assert "clOrdId" not in body
    assert order.client_order_id is None
    await ex.close()


async def test_response_client_order_id_wins_over_request(httpx_mock: HTTPXMock) -> None:
    """거래소가 돌려준 값이 정본이다(값을 바꿔 돌려주면 그걸 남긴다)."""
    httpx_mock.add_response(
        json={"code": "0", "msg": "", "data": [{"ordId": "o1", "clOrdId": "server1", "sCode": "0"}]}
    )
    ex = _swap()
    order = await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0, client_order_id="mine1")
    assert order.client_order_id == "server1"
    await ex.close()


def test_parse_order_carries_client_order_id() -> None:
    o = _parse_order("BTC/USDT:USDT", {"ordId": "o1", "clOrdId": "q7abc", "sz": "1", "state": "live"})
    assert o.client_order_id == "q7abc"


def test_parse_order_without_clordid_is_none() -> None:
    assert _parse_order("BTC/USDT:USDT", {"ordId": "o1", "sz": "1"}).client_order_id is None


# ── 우회 시도: 거래소가 받지 않을 값을 «보내보고» 답을 듣는 짓을 막는다 ──


@pytest.mark.parametrize(
    ("bad", "why"),
    [
        ("", "빈 문자열 — 멱등을 끄는 우회"),
        ("q7-abc", "하이픈 — 영숫자 아님"),
        ("q7 abc", "공백"),
        ("한글키1", "비ASCII"),
        ("x" * 33, "33자 — 상한 초과"),
    ],
)
async def test_invalid_client_order_id_is_rejected_before_the_network(
    httpx_mock: HTTPXMock, bad: str, why: str
) -> None:
    ex = _swap()
    with pytest.raises(InvalidOrderError):
        await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0, client_order_id=bad)
    assert httpx_mock.get_requests() == [], f"거부해야 할 값이 전송됐다: {why}"
    await ex.close()


async def test_max_length_client_order_id_is_accepted(httpx_mock: HTTPXMock) -> None:
    """경계값 32자는 통과해야 한다(과잉 차단도 결함이다)."""
    httpx_mock.add_response(json=_ACK)
    ex = _swap()
    await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0, client_order_id="x" * 32)
    body = json_lib.loads(httpx_mock.get_requests()[-1].content.decode())
    assert body["clOrdId"] == "x" * 32
    await ex.close()


async def test_duplicate_client_order_id_rejection_is_not_swallowed(httpx_mock: HTTPXMock) -> None:
    """우회 — 중복 clOrdId 거절을 «성공»으로 삼키지 않는다.

    🚨 정확한 sCode 는 아직 실측되지 않았다(2026-09-10 라이브 S7 은 캡 예산
    부족으로 중복 clOrdId 를 시험하지 못했다). 그래서 코드표가 아니라
    **거절이 그대로 올라온다**는 것만 지킨다.
    """
    httpx_mock.add_response(
        json={"code": "1", "msg": "", "data": [{"sCode": "51121", "sMsg": "Duplicated client order ID"}]}
    )
    ex = _swap()
    with pytest.raises(ExchangeError) as e:
        await ex.create_order("BTC/USDT:USDT", "buy", "limit", 1, 100.0, client_order_id="dup1")
    assert e.value.code == "51121"
    await ex.close()
