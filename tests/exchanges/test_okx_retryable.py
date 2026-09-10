"""A-8 — ``51008`` 은 «일시적·재시도 가능»으로 **분류만** 한다. 재시도는 안 한다.

SDK 는 정책을 갖지 않는다. 얼마나 기다릴지·몇 번 다시 볼지·언제 포기할지는
정산 인지 실행 루프(P-1)가 정하고, 여기서는 «이 거절은 나중에 성공할 수 있는
종류인가»만 말한다.

실측(09-10 원장): 매수 체결 직후 매도가 51008 로 27건 거절됐고, 약 70초 뒤
availBal 이 차자 같은 주문이 성공했다. 같은 51008 이라도 «영영 안 됨»이 아니다.
반대로 ``51000 Parameter tdMode error`` 는 몇 번을 다시 보내도 똑같다.
"""

from __future__ import annotations

import inspect
import re

import pytest
from pytest_httpx import HTTPXMock

from pycex.exceptions import (
    AuthenticationError,
    ExchangeError,
    InsufficientBalanceError,
    InvalidOrderError,
    PyCexError,
    RateLimitError,
    SettlementPendingError,
)
from pycex.exchanges import okx as okx_module
from pycex.exchanges.okx import OKX, _map_error


def _spot() -> OKX:
    ex = OKX(api_key="k", secret="s", passphrase="p")
    ex._acct_level = "1"
    return ex


def test_51008_is_classified_retryable() -> None:
    err = _map_error("51008", "Order failed. Insufficient ETH margin in account")
    assert isinstance(err, SettlementPendingError)
    assert err.retryable is True


def test_51008_stays_catchable_as_insufficient_balance() -> None:
    """기존 호출자가 잡던 타입을 깨지 않는다(하위호환)."""
    assert isinstance(_map_error("51008", "x"), InsufficientBalanceError)


def test_rate_limit_is_retryable() -> None:
    assert _map_error("50011", "Too Many Requests").retryable is True


@pytest.mark.parametrize(
    ("code", "cls"),
    [
        ("51000", ExchangeError),
        ("51603", ExchangeError),
        ("50111", AuthenticationError),
    ],
)
def test_permanent_errors_are_not_retryable(code: str, cls: type) -> None:
    err = _map_error(code, "nope")
    assert isinstance(err, cls)
    assert err.retryable is False


def test_default_is_not_retryable() -> None:
    """우회 1 — 기본값은 «재시도 불가»다. 모르는 오류를 낙관하지 않는다."""
    assert PyCexError().retryable is False
    assert InvalidOrderError("x").retryable is False
    assert _map_error("59999", "brand new code").retryable is False


async def test_51008_on_an_order_is_classified_and_sent_once(httpx_mock: HTTPXMock) -> None:
    """우회 2 — 분류했다고 SDK 가 대신 다시 보내지 않는다. 요청은 정확히 한 번."""
    httpx_mock.add_response(
        json={
            "code": "1",
            "msg": "",
            "data": [{"sCode": "51008", "sMsg": "Order failed. Insufficient ETH margin in account "}],
        }
    )
    ex = _spot()
    with pytest.raises(SettlementPendingError) as e:
        await ex.create_order("ETH/USDT", "sell", "market", 0.0041)
    assert e.value.retryable is True
    assert len([r for r in httpx_mock.get_requests() if r.url.path == "/api/v5/trade/order"]) == 1
    await ex.close()


async def test_51000_on_an_order_is_not_retryable(httpx_mock: HTTPXMock) -> None:
    """우회 3 — tdMode 오류를 «기다리면 되는 것»으로 분류하면 무한 헛주문이 된다."""
    httpx_mock.add_response(
        json={"code": "1", "msg": "", "data": [{"sCode": "51000", "sMsg": "Parameter tdMode error "}]}
    )
    ex = _spot()
    with pytest.raises(ExchangeError) as e:
        await ex.create_order("ETH/USDT", "buy", "market", 10)
    assert e.value.code == "51000"
    assert e.value.retryable is False
    await ex.close()


async def test_429_is_not_auto_retried(httpx_mock: HTTPXMock) -> None:
    """우회 4 — 재시도 가능으로 분류된 429 조차 SDK 가 스스로 다시 보내지 않는다."""
    httpx_mock.add_response(status_code=429, json={"code": "50011", "msg": "Too Many Requests"})
    ex = _spot()
    with pytest.raises(RateLimitError) as e:
        await ex.fetch_balance()
    assert e.value.retryable is True
    assert len(httpx_mock.get_requests()) == 1
    await ex.close()


def test_no_retry_loop_lives_in_the_adapter() -> None:
    """우회 5 — 소스에 재시도 루프·대기가 들어오는 것을 막는다.

    «분류만 한다»는 약속은 코드에 재시도가 없어야 성립한다.
    """
    source = inspect.getsource(okx_module)
    for pattern in (r"\basyncio\.sleep\b", r"\btime\.sleep\b", r"\bmax_retries\b", r"\bfor attempt\b"):
        assert re.search(pattern, source) is None, f"어댑터 안에 재시도/대기가 생겼다: {pattern}"
