"""A2-1 — 밖에서 꽂은 transport 는 **재빌드를 넘어 살아남는다**.

근거(프로브 2026-09-10, 이 레포 HEAD f328af7):
``ex._http._client = AsyncClient(transport=MockTransport(...))`` 로 «네트워크 0» 이라
믿은 재생 테스트가, ``*_sync`` 트윈의 2회차에서 조용히 **실제 OKX 로 나갔다.**
``_make_sync`` 는 호출마다 클라이언트를 닫고, ``_bind()`` 의 재빌드는
``_transport_factory`` 만 본다 — 주입은 클라이언트 «객체»로 들어왔으므로 사라진다.

    1회차 transport: MockTransport   → 목 도달 1
    2회차 transport: AsyncHTTPTransport → 목 도달 여전히 1, 값 78048.9 (진짜 시세)

그래서 클라이언트 «객체» 주입 경로(`_client` 세터)를 없애고,
:meth:`HTTPClient.set_transport_factory` 하나만 공개 주입 경로로 남긴다.
재빌드는 매번 그 팩토리를 부르므로 목은 절대 벗겨지지 않는다.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from pycex import OKX

_TICKER = {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "1"}]}


def _mocked_okx() -> tuple[OKX, list[str], list[httpx.MockTransport]]:
    seen: list[str] = []
    made: list[httpx.MockTransport] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=_TICKER)

    def factory() -> httpx.AsyncBaseTransport:
        t = httpx.MockTransport(handler)
        made.append(t)
        return t

    ex = OKX()
    ex._http.set_transport_factory(factory)
    return ex, seen, made


def _live_transports(ex: OKX) -> str:
    client = ex._http._client_obj
    assert client is not None
    return type(client._transport).__name__


def test_injected_transport_survives_the_sync_twin_rebuild() -> None:
    """돈 경로 재현 — 2·3회차도 목에 닿는다. 실 transport 는 한 번도 만들지 않는다."""
    ex, seen, made = _mocked_okx()
    for _ in range(3):
        assert ex.fetch_ticker_sync("BTC/USDT").last == 1.0
        assert _live_transports(ex) == "MockTransport"
    assert len(seen) == 3, "세 번 다 목 transport 로 갔어야 한다"
    assert len(made) == 3, "재빌드마다 팩토리를 다시 부른다"


def test_injected_transport_survives_close_and_reuse() -> None:
    """``close_sync()`` 로 명시적으로 닫아도 다음 호출이 실 네트워크로 승격되지 않는다."""
    ex, seen, _ = _mocked_okx()
    ex.fetch_ticker_sync("BTC/USDT")
    ex.close_sync()
    ex.fetch_ticker_sync("BTC/USDT")
    assert _live_transports(ex) == "MockTransport"
    assert len(seen) == 2


def test_async_after_sync_keeps_the_injected_transport() -> None:
    """루프가 바뀌는 순간(동기→async)이 유실 지점이었다. 여기서도 목이 유지된다."""
    ex, seen, _ = _mocked_okx()
    ex.fetch_ticker_sync("BTC/USDT")

    async def _later() -> None:
        await ex.fetch_ticker("BTC/USDT")
        assert _live_transports(ex) == "MockTransport"
        await ex.close()

    asyncio.run(_later())
    assert len(seen) == 2


# ── 우회 거부 ──


def test_bypass_1_client_object_injection_is_rejected() -> None:
    """우회 ① — 객체를 통째로 꽂는 옛 경로(`_client = ...`)는 이제 거부한다.

    조용히 받아주면 재빌드에서 벗겨져 실 네트워크로 나간다. 그래서 «못 쓴다»고
    바로 터뜨린다. AttributeError = 세터 없음(읽기 전용 프로퍼티).
    """
    ex = OKX()
    with pytest.raises(AttributeError):
        ex._http._client = httpx.AsyncClient(  # type: ignore[misc]
            base_url="https://www.okx.com",
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_TICKER)),
        )
    ex.close_sync()


def test_bypass_2_factory_returning_none_is_rejected() -> None:
    """우회 ② — «transport 없음»을 돌려주는 팩토리는 거부한다.

    ``None`` 을 그대로 httpx 에 넘기면 httpx 가 실 ``AsyncHTTPTransport`` 를
    끼워 넣는다 — 주입한 줄 알았는데 실 네트워크다. 만든 순간에 터뜨린다.
    """
    ex = OKX()
    ex._http.set_transport_factory(lambda: None)  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError, match="transport_factory"):
        ex.fetch_ticker_sync("BTC/USDT")


def test_bypass_3_event_hooks_are_not_a_smuggling_path() -> None:
    """우회 ③ — 훅을 달려고 클라이언트를 만져도 transport 는 팩토리 것이 이긴다."""
    ex, seen, _ = _mocked_okx()
    hooked: list[str] = []

    async def hook(request: httpx.Request) -> None:
        hooked.append(request.url.path)

    ex._http._client.event_hooks = {"request": [hook]}
    ex.fetch_ticker_sync("BTC/USDT")
    ex.fetch_ticker_sync("BTC/USDT")
    assert _live_transports(ex) == "MockTransport"
    assert hooked == ["/api/v5/market/ticker"] * 2, "훅은 재빌드를 넘어 유지된다"
    assert len(seen) == 2
