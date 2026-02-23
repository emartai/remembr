"""Tests for short-term memory service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.services.short_term import SessionMessage, ShortTermMemory


@pytest.mark.asyncio
async def test_priority_scoring_is_deterministic() -> None:
    """Same input message should always produce same score."""
    cache = AsyncMock()
    memory = ShortTermMemory(cache=cache, max_tokens=4000)

    ts = datetime(2024, 1, 1, tzinfo=UTC)
    message = SessionMessage(
        role="user",
        content="hello world",
        tokens=memory.token_count("hello world"),
        priority_score=0,
        timestamp=ts,
    )

    score_1 = memory._score_priority(message)
    score_2 = memory._score_priority(message)

    assert score_1 == score_2


@pytest.mark.asyncio
async def test_compression_removes_low_priority_messages() -> None:
    """Compression should drop lowest priority entries when token budget is exceeded."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=[])
    cache.set = AsyncMock(return_value=True)

    memory = ShortTermMemory(cache=cache, max_tokens=12)

    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    system_msg = SessionMessage(
        role="system",
        content="instruction",
        tokens=4,
        priority_score=0,
        timestamp=base_ts,
    )
    assistant_msg = SessionMessage(
        role="assistant",
        content="verbose response example",
        tokens=6,
        priority_score=0,
        timestamp=base_ts + timedelta(seconds=1),
    )
    user_msg = SessionMessage(
        role="user",
        content="question",
        tokens=4,
        priority_score=0,
        timestamp=base_ts + timedelta(seconds=2),
    )

    await memory.add_message("session-1", system_msg)
    cache.get = AsyncMock(return_value=cache.set.call_args.args[1])
    await memory.add_message("session-1", assistant_msg)
    cache.get = AsyncMock(return_value=cache.set.call_args.args[1])
    await memory.add_message("session-1", user_msg)

    context = await memory.get_context("session-1")

    roles = [msg.role for msg in context]
    assert sum(msg.tokens for msg in context) <= 12
    assert "assistant" not in roles
    assert "system" in roles
    assert "user" in roles
