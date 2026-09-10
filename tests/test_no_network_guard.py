"""A2-6 — 「네트워크 0」 이라는 주장 자체를 검사한다.

판정기도 틀린다. ``tests/conftest.py`` 의 차단이 실제로 무는지 확인하지 않으면,
차단이 조용히 풀린 날 A2-1 이 그대로 되돌아온다(그때도 테스트는 초록이었다).
"""

from __future__ import annotations

import socket

import httpx
import pytest

from tests.conftest import NetworkAccessDenied


def test_the_guard_blocks_a_real_outbound_request() -> None:
    """실제 거래소로 나가려 하면 «조용히 성공»이 아니라 즉시 터진다."""
    with pytest.raises(NetworkAccessDenied):
        httpx.get("https://www.okx.com/api/v5/market/ticker", params={"instId": "BTC-USDT"})


def test_the_guard_blocks_a_bare_socket_too() -> None:
    """우회 ① — httpx 를 피해 소켓을 직접 열어도 막힌다."""
    with pytest.raises(NetworkAccessDenied):
        socket.create_connection(("www.okx.com", 443), timeout=1)


def test_the_guard_leaves_loopback_alone() -> None:
    """우회 ② — 막느라 로컬까지 죽이면 아무도 안 쓴다. 루프백은 통과한다."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        client = socket.create_connection(server.getsockname(), timeout=1)
        client.close()
    finally:
        server.close()
