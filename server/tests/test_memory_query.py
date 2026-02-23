"""Unit tests for unified memory query engine."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.episodic import EpisodeSearchResult
from app.services.memory_query import MemoryQueryEngine, MemoryQueryRequest
from app.services.scoping import MemoryScope


class _FakeShortTerm:
    def __init__(self, messages: list[SimpleNamespace], delay: float = 0.0):
        self.messages = messages
        self.delay = delay

    async def get_context(self, _session_id: str) -> list[SimpleNamespace]:
        if self.delay:
            await asyncio.sleep(self.delay)
        return list(self.messages)


class _FakeEpisodic:
    def __init__(self, results: list[EpisodeSearchResult], delay: float = 0.0):
        self.results = results
        self.delay = delay

    async def search_semantic(self, **_kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return list(self.results)

    async def search_hybrid(self, **_kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return list(self.results)

    async def search_by_time(self, **_kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return [item.episode for item in self.results]

    async def get_session_history(self, **_kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return [item.episode for item in self.results]


@pytest.fixture
def scope() -> MemoryScope:
    return MemoryScope(org_id=str(uuid.uuid4()), level="org")


@pytest.mark.asyncio
async def test_query_runs_short_term_and_episodic_concurrently(scope: MemoryScope):
    now = datetime.now(UTC)
    short = _FakeShortTerm(
        messages=[
            SimpleNamespace(
                role="user",
                content="Need ideas for dinner",
                tokens=4,
                priority_score=1.0,
                timestamp=now,
            )
        ],
        delay=0.15,
    )
    episode = SimpleNamespace(
        id=uuid.uuid4(),
        session_id="s1",
        role="assistant",
        tags=["food"],
        created_at=now,
    )
    episodic = _FakeEpisodic(
        results=[EpisodeSearchResult(episode=episode, similarity_score=0.9)],
        delay=0.15,
    )

    engine = MemoryQueryEngine(short_term=short, episodic=episodic)
    req = MemoryQueryRequest(query="dinner", session_id="s1", search_mode="hybrid")

    started = asyncio.get_running_loop().time()
    result = await engine.query(scope, req)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 0.25
    assert result.total_results == 2
    assert result.query_time_ms > 0


@pytest.mark.asyncio
async def test_query_dedupes_episodes_and_merges_by_relevance(scope: MemoryScope):
    now = datetime.now(UTC)
    short = _FakeShortTerm(
        messages=[
            SimpleNamespace(
                role="assistant",
                content="Reset password from account settings",
                tokens=6,
                priority_score=1.0,
                timestamp=now - timedelta(seconds=5),
            )
        ]
    )

    duplicate_episode_id = uuid.uuid4()
    top_episode = SimpleNamespace(
        id=duplicate_episode_id,
        session_id="s2",
        role="assistant",
        tags=["support"],
        created_at=now - timedelta(seconds=10),
    )
    lower_duplicate = SimpleNamespace(
        id=duplicate_episode_id,
        session_id="s2",
        role="assistant",
        tags=["support"],
        created_at=now - timedelta(minutes=2),
    )
    episodic = _FakeEpisodic(
        results=[
            EpisodeSearchResult(episode=lower_duplicate, similarity_score=0.71),
            EpisodeSearchResult(episode=top_episode, similarity_score=0.95),
        ]
    )

    engine = MemoryQueryEngine(short_term=short, episodic=episodic)
    req = MemoryQueryRequest(query="reset password", session_id="s2", limit=5, search_mode="hybrid")

    result = await engine.query(scope, req)

    assert len(result.episodes) == 1
    assert result.episodes[0].similarity_score == pytest.approx(0.95)
    assert result.total_results == 2
    assert result.episodes[0].episode.id == duplicate_episode_id
