from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_health(live_client) -> None:
    data = await live_client.arequest("GET", "/health")
    assert isinstance(data, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_create_and_list_sessions(live_client) -> None:
    session = await live_client.create_session(metadata={"source": "sdk-integration-test"})
    sessions = await live_client.list_sessions(limit=20, offset=0)
    assert session.session_id
    assert any(s.session_id == session.session_id for s in sessions)
