"""A2-2 — 레이트 리밋은 ``HTTPClient`` 인스턴스의 수명에 묶인다.

근거(프로브 2026-09-10, HEAD f328af7): 같은 40회를

    sync 40회 소요: 0.03s      ← 제한이 없는 것과 같다
    async 40회 소요: 3.02s     ← rate=10/s 가 걸린 정상

``*_sync`` 트윈은 호출마다 루프를 새로 만들고, ``_bind()`` 는 루프가 바뀔 때마다
``RateLimiter`` 를 통째로 새로 만들었다. 새 리미터는 토큰이 꽉 찬 상태로 시작하니
매 호출이 «첫 호출»이 된다 — 40회를 0.03초에 쏴도 아무도 막지 않는다.
거래소가 보는 것은 IP 이고, 그 끝은 429 와 차단이다.

고친 방식: 토큰 상태(``_tokens``/``_last``)는 인스턴스 수명 동안 유지하고,
루프에 묶이는 것은 ``asyncio.Lock`` 뿐이므로 **락만** 루프가 바뀔 때 다시 만든다.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from pycex.http import HTTPClient, RateLimiter

_BODY = {"ok": True}


def _client(rate: float) -> HTTPClient:
    c = HTTPClient("https://example.invalid", rate=rate)
    c.set_transport_factory(lambda: httpx.MockTransport(lambda r: httpx.Response(200, json=_BODY)))
    return c


def _call_once(c: HTTPClient) -> None:
    """``*_sync`` 트윈과 같은 방식 — 호출마다 새 루프를 만들고 끝나면 닫는다."""

    async def _run() -> None:
        await c.get("/ping")
        await c.close()

    asyncio.run(_run())


def test_rate_limit_holds_across_sync_style_loops() -> None:
    """루프가 바뀌어도 토큰 예산은 이어진다.

    rate=20/s 는 처음 20회가 공짜(버킷이 차 있다)이고 그 뒤 10회는 0.05초씩
    기다려야 하므로 30회는 최소 0.5초 가까이 걸린다. 리미터가 매번 새로
    만들어지면 이 값은 0.0x 초로 떨어진다.
    """
    c = _client(20.0)
    t0 = time.monotonic()
    for _ in range(30):
        _call_once(c)
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.35, f"sync 30회가 {elapsed:.3f}s — 리미터가 무력하다"


def test_limiter_object_survives_every_rebuild() -> None:
    """시계에 기대지 않는 판정 — 리미터 인스턴스와 토큰 잔량이 그대로다."""
    c = _client(50.0)
    limiter = c._limiter
    _call_once(c)
    tokens_after_one = c._limiter._tokens
    _call_once(c)
    assert c._limiter is limiter, "재빌드가 리미터를 갈아치웠다"
    assert c._limiter._tokens < tokens_after_one, "두 번째 호출이 예산을 소비하지 않았다"


def test_async_and_sync_share_one_budget() -> None:
    """동기·비동기를 섞어 써도 예산은 하나다."""
    c = _client(50.0)
    _call_once(c)
    before = c._limiter._tokens

    async def _run() -> None:
        await c.get("/ping")
        await c.close()

    asyncio.run(_run())
    assert c._limiter._tokens < before


# ── 우회 거부 ──


def test_bypass_1_close_does_not_refill_the_bucket() -> None:
    """우회 ① — ``close()`` 로 클라이언트를 닫아도 버킷은 리필되지 않는다."""
    c = _client(50.0)
    _call_once(c)  # 안에서 close() 까지 한다
    after = c._limiter._tokens
    assert after < 50.0
    asyncio.run(c.close())
    assert c._limiter._tokens == pytest.approx(after), "close 가 예산을 되살렸다"


def test_bypass_2_new_loop_does_not_reset_the_bucket() -> None:
    """우회 ② — 루프를 갈아타는 것으로는 예산을 되살리지 못한다.

    락은 루프에 묶이므로 다시 만들어야 하지만(안 만들면 다른 루프에서
    ``RuntimeError``), 토큰은 이어져야 한다.
    """
    limiter = RateLimiter(50.0)

    async def _take(n: int) -> None:
        for _ in range(n):
            await limiter.acquire()

    asyncio.run(_take(5))
    after_first_loop = limiter._tokens
    asyncio.run(_take(5))  # 새 루프 — 여기서 터지지도, 리필되지도 않아야 한다
    assert limiter._tokens < after_first_loop, "새 루프가 버킷을 리필했다"
