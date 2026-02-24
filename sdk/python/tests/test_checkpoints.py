from __future__ import annotations

import httpx
import pytest

from remembr import RemembrClient


@pytest.mark.asyncio
async def test_checkpoint_restore_cycle(mock_client) -> None:
    client, api = mock_client
    api.enqueue(
        httpx.Response(
            201,
            json={
                "data": {
                    "checkpoint_id": "cp_123",
                    "created_at": "2026-01-01T00:00:00Z",
                    "message_count": 3,
                }
            },
        )
    )
    api.enqueue(
        httpx.Response(
            200,
            json={
                "data": {
                    "request_id": "req_restore",
                    "restored_message_count": 3,
                    "checkpoint_created_at": "2026-01-01T00:00:00Z",
                }
            },
        )
    )

    checkpoint = await client.checkpoint("sess_123")
    restore = await client.restore("sess_123", checkpoint.checkpoint_id)

    assert checkpoint.message_count == 3
    assert restore["restored_message_count"] == 3


@pytest.mark.asyncio
async def test_list_checkpoints_ordered(mock_client) -> None:
    client, api = mock_client
    checkpoints = [
        {"checkpoint_id": "cp_new", "created_at": "2026-01-01T00:02:00Z", "message_count": 5},
        {"checkpoint_id": "cp_old", "created_at": "2026-01-01T00:01:00Z", "message_count": 2},
    ]
    api.enqueue(httpx.Response(200, json={"data": {"checkpoints": checkpoints}}))

    result = await client.list_checkpoints("sess_123")
    assert [c.checkpoint_id for c in result] == ["cp_new", "cp_old"]
