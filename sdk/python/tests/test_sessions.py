from __future__ import annotations

import httpx
import pytest

from remembr import RemembrClient


@pytest.mark.asyncio
async def test_create_session_returns_session(mock_client, sample_session) -> None:
    client, api = mock_client
    api.enqueue(httpx.Response(201, json={"data": sample_session}))

    session = await client.create_session(metadata={"topic": "tests"})
    assert session.session_id == sample_session["session_id"]
    assert session.org_id == sample_session["org_id"]


@pytest.mark.asyncio
async def test_get_session_returns_session(mock_client, sample_session) -> None:
    client, api = mock_client
    api.enqueue(httpx.Response(200, json={"data": {"request_id": "req_1", "session": sample_session}}))

    session = await client.get_session("sess_123")
    assert session.session_id == "sess_123"
    assert session.metadata == {"topic": "tests"}


@pytest.mark.asyncio
async def test_list_sessions_returns_paginated(mock_client, sample_session) -> None:
    client, api = mock_client
    s2 = {**sample_session, "session_id": "sess_456"}
    api.enqueue(
        httpx.Response(
            200,
            json={
                "data": {
                    "request_id": "req_list",
                    "org_id": "org_123",
                    "sessions": [sample_session, s2],
                    "total": 2,
                    "limit": 2,
                    "offset": 0,
                }
            },
        )
    )

    sessions = await client.list_sessions(limit=2, offset=0)
    assert len(sessions) == 2
    assert sessions[0].session_id == "sess_123"
    assert sessions[1].session_id == "sess_456"
