"""HTTP client with rate limiting and error handling."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from pycex.exceptions import ExchangeError, NetworkError, PyCexError, RateLimitError

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


class HTTPClient:
    """Async HTTP client for exchange API calls."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        rate: float = 10.0,
        default_headers: dict[str, str] | None = None,
        error_mapper: Callable[[int, dict[str, Any]], PyCexError | None] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_headers = default_headers or {}
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout, headers=self._default_headers)
        self._limiter = RateLimiter(rate)
        self._error_mapper = error_mapper

    async def get(
        self, path: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any:
        await self._limiter.acquire()
        try:
            resp = await self._client.get(path, params=params, headers=headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    async def post(
        self,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        await self._limiter.acquire()
        try:
            resp = await self._client.post(path, json=data, headers=headers, params=params)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    async def delete(
        self, path: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any:
        await self._limiter.acquire()
        try:
            resp = await self._client.delete(path, params=params, headers=headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    async def post_raw(self, path: str, *, body: str, headers: dict[str, str] | None = None) -> Any:
        """POST a pre-serialized JSON body verbatim (async only — no sync twin).

        Sends ``body`` exactly as given via ``content=`` rather than handing a
        dict to httpx's own ``json=`` encoding (which re-serializes with its
        own separators, e.g. compact vs. ``json.dumps``'s default ``", "``/
        ``": "``). Callers whose signature covers the literal byte string being
        sent — e.g. OKX, whose prehash is ``ts + method + path + body`` — need
        the signed string and the wire bytes to be byte-for-byte identical;
        going through ``post()``'s ``json=`` would re-serialize and silently
        break every such signature.
        """
        await self._limiter.acquire()
        merged_headers = {"Content-Type": "application/json", **(headers or {})}
        try:
            resp = await self._client.post(path, content=body.encode(), headers=merged_headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    async def post_form(
        self, path: str, *, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any:
        """POST an ``application/x-www-form-urlencoded`` body (async only — no sync twin).

        Encodes ``data`` with :func:`urllib.parse.urlencode` ourselves (rather than
        handing the dict to httpx's own ``data=`` form encoding) so that callers who
        need to sign the exact bytes being sent — e.g. Korbit, whose signature covers
        the literal encoded body — get a byte-for-byte match between what they signed
        and what goes over the wire.
        """
        await self._limiter.acquire()
        body = urlencode(data or {}, doseq=True)
        merged_headers = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
        try:
            resp = await self._client.post(path, content=body, headers=merged_headers)
            return self._handle_response(resp)
        except httpx.HTTPError as e:
            raise NetworkError(str(e)) from e

    def _handle_response(self, resp: httpx.Response) -> Any:
        """Return the parsed JSON body. Shape (dict or list) depends on the endpoint."""
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            err = RateLimitError("Rate limit exceeded", exchange="")
            err.retry_after = float(ra) if ra and ra.replace(".", "", 1).isdigit() else None
            raise err
        try:
            data: Any = resp.json()
        except ValueError:
            data = {"raw_text": resp.text}
        if resp.status_code >= 400:
            err_dict: dict[str, Any] = data if isinstance(data, dict) else {}
            if self._error_mapper is not None:
                mapped = self._error_mapper(resp.status_code, err_dict)
                if mapped is not None:
                    raise mapped
            msg = err_dict.get("msg") or err_dict.get("message") or str(data)
            code = err_dict.get("code") or err_dict.get("ret_code") or resp.status_code
            raise ExchangeError(msg, code=code)
        return data

    async def close(self) -> None:
        await self._client.aclose()
