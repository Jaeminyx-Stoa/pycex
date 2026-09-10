"""A-7 — 자산별 **가용 잔고(availBal)** 를 SDK 가 노출한다.

🚨 51008 의 정답은 «재시도»가 아니라 **가용 잔고 확인**이다. 09-10 라이브에서
현물 매수 체결 직후 매도가 약 70초간 51008 로 거절됐다(2회 재현). 정산이
끝났는지는 로컬 장부가 아니라 거래소의 availBal 로만 알 수 있다.

그래서 이 함수는 **매번 다시 묻는다**. 캐시하면 «정산됐다»를 캐시하는 것과
같고, 그건 정산 인지가 아니다. 재시도 정책은 여기 없다(A-8·P-1).
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest
from pytest_httpx import HTTPXMock

from pycex.exceptions import AuthenticationError
from pycex.exchanges.okx import OKX


def _balance(**avail: str) -> dict:
    details = [
        {"ccy": ccy, "availBal": v, "frozenBal": "0", "cashBal": "999", "eq": "999"} for ccy, v in avail.items()
    ]
    return {"code": "0", "msg": "", "data": [{"details": details}]}


def _ex() -> OKX:
    return OKX(api_key="k", secret="s", passphrase="p")


async def test_returns_available_balance_for_the_asset(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_balance(USDT="21.42545377472396"))
    ex = _ex()
    assert await ex.fetch_available_balance("USDT") == pytest.approx(21.42545377472396)
    await ex.close()


async def test_queries_only_that_currency_and_signs_the_query(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_balance(ETH="0.001050943"))
    ex = _ex()
    await ex.fetch_available_balance("ETH")
    req = httpx_mock.get_requests()[-1]
    assert req.url.path == "/api/v5/account/balance"
    assert req.url.params["ccy"] == "ETH"
    message = req.headers["OK-ACCESS-TIMESTAMP"] + "GET" + req.url.raw_path.decode()
    expected = base64.b64encode(hmac.new(b"s", message.encode(), hashlib.sha256).digest()).decode()
    assert req.headers["OK-ACCESS-SIGN"] == expected, "쿼리까지 포함해 서명해야 한다"
    await ex.close()


async def test_asset_lookup_is_case_insensitive(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_balance(USDT="5"))
    ex = _ex()
    assert await ex.fetch_available_balance("usdt") == 5.0
    await ex.close()


def test_available_balance_has_a_sync_twin(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_balance(USDT="7"))
    ex = _ex()
    assert ex.fetch_available_balance_sync("USDT") == 7.0


# ── 우회 시도 ──


async def test_every_call_re_measures(httpx_mock: HTTPXMock) -> None:
    """우회 1 — 캐시 금지. 정산은 «두 번째로 물었을 때» 끝나 있는 것이다."""
    httpx_mock.add_response(json=_balance(ETH="0"))
    httpx_mock.add_response(json=_balance(ETH="0.0041"))
    ex = _ex()
    assert await ex.fetch_available_balance("ETH") == 0.0
    assert await ex.fetch_available_balance("ETH") == pytest.approx(0.0041)
    assert len([r for r in httpx_mock.get_requests() if r.url.path == "/api/v5/account/balance"]) == 2
    await ex.close()


async def test_unknown_asset_is_zero_not_a_total(httpx_mock: HTTPXMock) -> None:
    """우회 2 — 없는 자산은 0 이다(다른 자산 잔고를 대신 돌려주지 않는다)."""
    httpx_mock.add_response(json=_balance(USDT="100"))
    ex = _ex()
    assert await ex.fetch_available_balance("BTC") == 0.0
    await ex.close()


async def test_it_is_avail_bal_not_cash_bal(httpx_mock: HTTPXMock) -> None:
    """우회 3 — 정산 안 된 잔고(cashBal·eq)를 «가용»이라 부르지 않는다.

    이 구분이 무너지면 51008 을 그대로 다시 맞는다.
    """
    httpx_mock.add_response(
        json={
            "code": "0",
            "msg": "",
            "data": [{"details": [{"ccy": "ETH", "availBal": "0", "cashBal": "0.0041", "eq": "0.0041"}]}],
        }
    )
    ex = _ex()
    assert await ex.fetch_available_balance("ETH") == 0.0
    await ex.close()


async def test_error_is_not_swallowed_as_zero(httpx_mock: HTTPXMock) -> None:
    """우회 4 — 조회 실패를 «잔고 0» 으로 뭉개지 않는다(fail-closed 는 예외다)."""
    httpx_mock.add_response(json={"code": "50111", "msg": "Invalid OK-ACCESS-KEY", "data": []})
    ex = _ex()
    with pytest.raises(AuthenticationError):
        await ex.fetch_available_balance("USDT")
    await ex.close()


async def test_sdk_does_not_retry_on_its_own(httpx_mock: HTTPXMock) -> None:
    """우회 5 — SDK 안에 재시도 루프가 없다. 정책은 호출자(P-1)의 것이다."""
    httpx_mock.add_response(json=_balance(USDT="1"))
    ex = _ex()
    await ex.fetch_available_balance("USDT")
    assert len(httpx_mock.get_requests()) == 1
    await ex.close()


def test_base_default_uses_fetch_balance() -> None:
    """다른 거래소도 같은 계약을 갖는다 — 기본 구현은 fetch_balance 에서 뽑는다."""
    import asyncio

    from pycex.base import BaseExchange
    from pycex.models import Balance, BalanceEntry

    class _Fake:
        async def fetch_balance(self) -> Balance:
            return Balance(assets=[BalanceEntry(asset="USDT", free=3.0, locked=1.0)])

        fetch_available_balance = BaseExchange.fetch_available_balance

    ex = _Fake()
    assert asyncio.run(ex.fetch_available_balance("USDT")) == 3.0
    assert asyncio.run(ex.fetch_available_balance("BTC")) == 0.0


def test_request_hook_sees_no_credentials_in_the_url(httpx_mock: HTTPXMock) -> None:
    """우회 6 — 비밀값은 헤더로만 간다. 쿼리에 키가 실리지 않는다."""
    httpx_mock.add_response(json=_balance(USDT="1"))
    ex = _ex()
    ex.fetch_available_balance_sync("USDT")
    url = str(httpx_mock.get_requests()[-1].url)
    assert "k" not in url.split("?")[-1].replace("ccy=USDT", "")
