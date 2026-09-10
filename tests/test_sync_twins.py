"""A-1 — ``*_sync`` 트윈이 **같은 인스턴스의 반복 호출**에서 동작한다.

근거(실측 2026-09-10): ``base.py`` 의 ``_make_sync`` 는 호출마다 ``asyncio.run`` 으로
새 이벤트 루프를 만들고, 끝나면 그 루프를 닫는다. 그런데 ``HTTPClient`` 는
``httpx.AsyncClient``(=커넥션 풀)를 생성자에서 한 번 만들어 첫 루프에 묶는다.
그래서 **두 번째 호출부터** ``RuntimeError: Event loop is closed`` 로 죽는다.
이 상태로 ``CexAdapter`` 를 운영에 붙이면 **두 번째 주문에서 죽는다.**

여기서 쓰는 ``LoopBoundTransport`` 는 그 실패를 흉내내는 게 아니라 **그대로
재현**한다 — httpx 의 실제 ``AsyncHTTPTransport`` 도 자기 풀을 처음 쓴 루프에
묶고, 닫힌 루프에서 다시 쓰이면 같은 ``RuntimeError`` 를 낸다.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pycex import OKX

_TICKER = {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "1"}]}


class LoopBoundTransport(httpx.AsyncBaseTransport):
    """실제 커넥션 풀과 같은 규칙: 처음 쓰인 루프에서만 동작한다."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise RuntimeError("Event loop is closed")
        return httpx.Response(200, json=_TICKER)


def _loop_bound_okx() -> tuple[OKX, list[LoopBoundTransport]]:
    made: list[LoopBoundTransport] = []

    def factory() -> httpx.AsyncBaseTransport:
        t = LoopBoundTransport()
        made.append(t)
        return t

    ex = OKX()
    ex._http.set_transport_factory(factory)  # A2-1 — 공개 주입 경로 하나뿐이다
    return ex, made


def test_sync_twin_repeats_on_same_instance() -> None:
    """호출마다 그 루프의 풀을 새로 얻는다 — 3회 연속 성공."""
    ex, made = _loop_bound_okx()
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
    assert len(made) == 3, "루프마다 새 전송계층을 만들어야 한다"


def test_sync_twin_repeats_after_close_sync() -> None:
    """``close_sync()`` 뒤에도 다음 호출이 되살아난다 — 커넥션 풀은 루프 소유물이다."""
    ex, _ = _loop_bound_okx()
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
    ex.close_sync()
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
    ex.close_sync()


def test_sync_twin_releases_pool_before_its_loop_dies() -> None:
    """동기 호출이 끝나면 그 루프의 클라이언트는 닫혀 있다(풀 유실 금지)."""
    ex, _ = _loop_bound_okx()
    ex.fetch_ticker_sync("BTC/USDT")
    assert ex._http._client_obj is not None
    assert ex._http._client_obj.is_closed is True


def test_sync_then_async_on_same_instance() -> None:
    """동기 호출로 루프를 한 번 태운 인스턴스를 이어서 async 로 쓸 수 있다."""
    ex, made = _loop_bound_okx()
    assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0

    async def _later() -> float:
        t = await ex.fetch_ticker("BTC/USDT")
        await ex.close()
        return t.last

    assert asyncio.run(_later()) == 1.0
    assert len(made) == 2


def test_async_calls_in_one_loop_reuse_one_client() -> None:
    """반대 방향의 회귀 — 한 루프 안의 연속 호출까지 매번 새 풀을 만들지는 않는다."""
    ex, made = _loop_bound_okx()

    async def _run() -> None:
        await ex.fetch_ticker("BTC/USDT")
        await ex.fetch_ticker("BTC/USDT")
        await ex.close()

    asyncio.run(_run())
    assert len(made) == 1


def test_sync_twin_rejected_inside_running_loop() -> None:
    """우회 1 — 실행 중인 루프 안에서 ``*_sync`` 를 부르는 것은 거부한다.

    (여기서 ``asyncio.run`` 을 중첩하면 루프가 깨진다. 조용히 봐주지 않는다.)
    """

    async def _inside() -> None:
        ex = OKX()
        with pytest.raises(RuntimeError, match="running event loop"):
            ex.fetch_ticker_sync("BTC/USDT")
        await ex.close()

    asyncio.run(_inside())


def test_close_sync_rejected_inside_running_loop() -> None:
    """우회 2 — ``close_sync()`` 도 실행 중인 루프 안에서는 거부한다."""

    async def _inside() -> None:
        ex = OKX()
        with pytest.raises(RuntimeError, match="running event loop"):
            ex.close_sync()
        await ex.close()

    asyncio.run(_inside())


def test_two_instances_do_not_share_a_loop_bound_client(httpx_mock: HTTPXMock) -> None:
    """우회 3 — 인스턴스마다 자기 클라이언트를 갖는다(한쪽 close 가 다른 쪽을 죽이지 않는다)."""
    httpx_mock.add_response(json=_TICKER, is_reusable=True)
    a, b = OKX(), OKX()
    assert a.fetch_ticker_sync("BTC/USDT").last == 1.0
    a.close_sync()
    assert b.fetch_ticker_sync("BTC/USDT").last == 1.0
    b.close_sync()


def test_injected_transport_is_adopted_not_replaced() -> None:
    """우회 4 — 밖에서 꽂아준 전송계층(기록 픽스처)과 요청 훅을 첫 호출이 삼키지 않는다.

    (A2-1 이후 주입 경로는 :meth:`HTTPClient.set_transport_factory` 하나다.
    클라이언트 «객체» 주입은 재빌드에서 벗겨지므로 거부된다 —
    ``tests/test_transport_injection.py`` 참조.)
    """
    seen: list[str] = []

    async def hook(request: httpx.Request) -> None:
        seen.append(request.url.path)

    ex = OKX()
    ex._http.set_transport_factory(
        lambda: httpx.MockTransport(lambda r: httpx.Response(200, json=_TICKER))
    )
    ex._http._client.event_hooks = {"request": [hook]}

    async def _run() -> None:
        await ex.fetch_ticker("BTC/USDT")
        await ex.close()

    asyncio.run(_run())
    assert seen == ["/api/v5/market/ticker"]
