"""Unit tests for EpisodicMemory service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.episodic import EpisodicMemory
from app.services.scoping import MemoryScope


class _BackgroundDB:
    def __init__(self, episode):
        self.episode = episode
        self.added = []
        self.committed = False

    async def get(self, _model, _id):
        return self.episode

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True


class _SessionFactory:
    def __init__(self, db):
        self.db = db

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def scope() -> MemoryScope:
    return MemoryScope(org_id=str(uuid.uuid4()), level="org")


@pytest.mark.asyncio
async def test_log_is_non_blocking_and_schedules_embedding(
    scope: MemoryScope,
    monkeypatch: pytest.MonkeyPatch,
):
    fake_db = object()
    svc = EpisodicMemory(db=fake_db)

    fake_episode = SimpleNamespace(id=uuid.uuid4())
    mocked_log = AsyncMock(return_value=fake_episode)
    monkeypatch.setattr("app.services.episodic.episode_repo.log_episode", mocked_log)

    scheduled = {}

    def _capture_create_task(coro):
        scheduled["coro"] = coro
        coro.close()
        return object()

    monkeypatch.setattr("app.services.episodic.asyncio.create_task", _capture_create_task)

    episode = await svc.log(scope=scope, role="user", content="hello")

    assert episode is fake_episode
    mocked_log.assert_awaited_once()
    assert "coro" in scheduled


@pytest.mark.asyncio
async def test_replay_session_orders_ascending(scope: MemoryScope, monkeypatch: pytest.MonkeyPatch):
    svc = EpisodicMemory(db=object())

    e1 = SimpleNamespace(created_at=datetime(2026, 1, 2, tzinfo=UTC), id=uuid.uuid4())
    e2 = SimpleNamespace(created_at=datetime(2026, 1, 1, tzinfo=UTC), id=uuid.uuid4())

    mocked_list = AsyncMock(return_value=[e1, e2])
    monkeypatch.setattr("app.services.episodic.episode_repo.list_episodes", mocked_list)

    replay = await svc.replay_session(scope=scope, session_id=str(uuid.uuid4()))

    assert [item.id for item in replay] == [e2.id, e1.id]


@pytest.mark.asyncio
async def test_background_embedding_persists_record(scope: MemoryScope):
    episode = SimpleNamespace(id=uuid.uuid4(), org_id=uuid.uuid4())
    background_db = _BackgroundDB(episode=episode)
    embedding_service = SimpleNamespace(
        model="fake-model",
        generate_embedding=AsyncMock(return_value=([0.1, 0.2], 2)),
    )

    svc = EpisodicMemory(
        db=object(),
        embedding_service=embedding_service,
        session_factory=_SessionFactory(background_db),
    )

    await svc._generate_and_store_embedding(episode.id, "content")

    assert background_db.committed is True
    assert len(background_db.added) == 1
    added = background_db.added[0]
    assert added.episode_id == episode.id
    assert added.dimensions == 2


@pytest.mark.asyncio
async def test_search_by_tags_delegates_to_repo(
    scope: MemoryScope,
    monkeypatch: pytest.MonkeyPatch,
):
    svc = EpisodicMemory(db=object())

    mocked_list = AsyncMock(return_value=[])
    monkeypatch.setattr("app.services.episodic.episode_repo.list_episodes", mocked_list)

    await svc.search_by_tags(scope=scope, tags=["a"], limit=3)

    mocked_list.assert_awaited_once()
    kwargs = mocked_list.await_args.kwargs
    assert kwargs["tags"] == ["a"]
    assert kwargs["limit"] == 3
