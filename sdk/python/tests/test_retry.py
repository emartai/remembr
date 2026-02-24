from __future__ import annotations

import httpx
import pytest
from tenacity import wait_none

from remembr import RemembrClient
from remembr.exceptions import AuthenticationError, NotFoundError, RateLimitError, RemembrError


@pytest.mark.asyncio
async def test_retries_on_429(monkeypatch: pytest.MonkeyPatch, mock_client) -> None:
    client, api = mock_client
    monkeypatch.setattr("remembr.client.wait_exponential", lambda **_: wait_none())

    api.enqueue(httpx.Response(429, json={"error": {"message": "rate limited", "code": "RATE_LIMIT_ERROR"}}))
    api.enqueue(httpx.Response(429, json={"error": {"message": "rate limited", "code": "RATE_LIMIT_ERROR"}}))
    api.enqueue(httpx.Response(429, json={"error": {"message": "rate limited", "code": "RATE_LIMIT_ERROR"}}))
    api.enqueue(httpx.Response(429, json={"error": {"message": "rate limited", "code": "RATE_LIMIT_ERROR"}}))

    with pytest.raises(RateLimitError):
        await client.arequest("GET", "/sessions")

    assert len(api.requests) == 4


@pytest.mark.asyncio
async def test_retries_on_503_then_succeeds(monkeypatch: pytest.MonkeyPatch, mock_client) -> None:
    client, api = mock_client
    monkeypatch.setattr("remembr.client.wait_exponential", lambda **_: wait_none())

    api.enqueue(httpx.Response(503, json={"error": {"message": "unavailable", "code": "INTERNAL_ERROR"}}))
    api.enqueue(httpx.Response(200, json={"data": {"ok": True}}))

    data = await client.arequest("GET", "/health")
    assert data["ok"] is True
    assert len(api.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (400, RemembrError),
        (401, AuthenticationError),
        (404, NotFoundError),
    ],
)
async def test_no_retry_on_client_errors(mock_client, status_code: int, exception_type: type[Exception]) -> None:
    client, api = mock_client
    api.enqueue(httpx.Response(status_code, json={"error": {"message": "client error", "code": "BAD"}}))

    with pytest.raises(exception_type):
        await client.arequest("GET", "/sessions")

    assert len(api.requests) == 1
