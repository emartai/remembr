from __future__ import annotations

import httpx
import pytest

from remembr import RemembrClient
from remembr.exceptions import AuthenticationError


@pytest.mark.asyncio
async def test_authentication_error_on_401(mock_client: tuple[RemembrClient, object]) -> None:
    client, api = mock_client
    api.enqueue(
        httpx.Response(
            401,
            json={
                "error": {
                    "message": "Unauthorized",
                    "code": "AUTHENTICATION_ERROR",
                    "request_id": "req_auth",
                }
            },
        )
    )

    with pytest.raises(AuthenticationError):
        await client.arequest("GET", "/sessions")


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REMEMBR_API_KEY", "env-key")
    client = RemembrClient()
    assert client.api_key == "env-key"


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REMEMBR_API_KEY", raising=False)
    with pytest.raises(AuthenticationError):
        RemembrClient(api_key=None)
