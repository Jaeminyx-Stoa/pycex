"""Shared test helpers — and the guard that makes «no network» true.

A2-1 (2026-09-10): a recorded-fixture test believed it was offline and was not.
The injected mock was dropped on the second ``*_sync`` call and the request went
to the live venue — the test still passed, because a real 200 parses just as
well as a recorded one. A suite that can silently reach a money endpoint is not
verifying anything, so outbound sockets are blocked here for every test that is
not marked ``live``.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(exchange: str, name: str) -> Any:
    return json.loads((FIXTURES / exchange / f"{name}.json").read_text())


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class NetworkAccessDenied(RuntimeError):
    """A test that is not marked ``live`` tried to open a real connection."""


def _host_of(address: Any) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address)


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Block outbound sockets unless the test is marked ``live``.

    Loopback stays open so a local fake server is still possible.
    """
    if request.node.get_closest_marker("live"):
        return

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create = socket.create_connection

    def _deny(address: Any) -> None:
        host = _host_of(address)
        if host not in _LOOPBACK:
            raise NetworkAccessDenied(
                f"이 테스트는 네트워크를 쓰지 않아야 한다 — {host} 로 나가려 했다. "
                f"실제 거래소가 필요하면 @pytest.mark.live 를 붙여라."
            )

    def connect(self: socket.socket, address: Any) -> Any:
        _deny(address)
        return real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> Any:
        _deny(address)
        return real_connect_ex(self, address)

    def create_connection(address: Any, *a: Any, **kw: Any) -> Any:
        _deny(address)
        return real_create(address, *a, **kw)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
