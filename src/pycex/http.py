"""HTTP client with rate limiting and error handling."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from pycex.exceptions import ExchangeError, NetworkError, RateLimitError

logger = logging.getLogger("pycex")


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float) -> None:
        self._rate = rate
        self._tokens = rate
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last = now
            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0
                self._last = time.monotonic()
            else:
                self._tokens -= 1

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
        self._last = now
        if self._tokens < 1:
            wait = (1 - self._tokens) / self._rate
            time.sleep(wait)
            self._tokens = 0
            self._last = time.monotonic()
        else:
            self._tokens -= 1


class HTTPClient:
    """Async HTTP client for exchange API calls."""

    def __init__(
        self, base_url: str, *, timeout: float = 30.0, rate: float = 10.0, default_headers: dict | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_headers = default_headers or {}
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout, headers=self._default_headers)
        self._sync_client = httpx.Client(base_url=self._base_url, timeout=timeout, headers=self._default_headers)
        self._limiter = RateLimiter(rate)

    async def get(self, path: str, *, params: dict | None = None, headers: dict | None = None) -> dict[str, Any]:
        await self._limiter.acquire()
        try:
            resp = await self._client.get(path, params=params, headers=headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    async def post(
        self, path: str, *, data: dict | None = None, headers: dict | None = None, params: dict | None = None
    ) -> dict[str, Any]:
        await self._limiter.acquire()
        try:
            resp = await self._client.post(path, json=data, headers=headers, params=params)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    def sync_get(self, path: str, *, params: dict | None = None, headers: dict | None = None) -> dict[str, Any]:
        self._limiter.wait()
        try:
            resp = self._sync_client.get(path, params=params, headers=headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    def sync_post(
        self, path: str, *, data: dict | None = None, headers: dict | None = None, params: dict | None = None
    ) -> dict[str, Any]:
        self._limiter.wait()
        try:
            resp = self._sync_client.post(path, json=data, headers=headers, params=params)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    def _handle_response(self, resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded", exchange="")
        data: dict[str, Any] = resp.json()
        if resp.status_code >= 400:
            msg = data.get("msg") or data.get("message") or str(data)
            code = data.get("code") or data.get("ret_code") or resp.status_code
            raise ExchangeError(msg, code=code)
        return data

    async def close(self) -> None:
        await self._client.aclose()
        self._sync_client.close()

    def sync_close(self) -> None:
        self._sync_client.close()
