import pytest
from pytest_httpx import HTTPXMock

from pycex.exceptions import ExchangeError, InsufficientBalanceError, RateLimitError
from pycex.http import HTTPClient


async def test_429_carries_retry_after(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "3"}, json={})
    c = HTTPClient("https://x.test", rate=1000)
    with pytest.raises(RateLimitError) as e:
        await c.get("/p")
    assert e.value.retry_after == 3.0
    await c.close()


async def test_delete_goes_through_handler(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="DELETE", status_code=400, json={"code": -2011, "msg": "Unknown order"})
    c = HTTPClient("https://x.test", rate=1000)
    with pytest.raises(ExchangeError) as e:
        await c.delete("/o", params={"id": "1"})
    assert e.value.code == -2011
    await c.close()


async def test_error_mapper_hook(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=400, json={"code": -2010, "msg": "insufficient"})

    def mapper(status: int, data: dict) -> ExchangeError | None:
        return InsufficientBalanceError(data["msg"], code=data["code"]) if data.get("code") == -2010 else None

    c = HTTPClient("https://x.test", rate=1000, error_mapper=mapper)
    with pytest.raises(InsufficientBalanceError):
        await c.get("/p")
    await c.close()
