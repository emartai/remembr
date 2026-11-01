import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.api.v1.memory import MemoryQueryEngine, MemoryQueryRequest
from app.services.scoping import MemoryScope
from app.services.tag_filter import TagFilter


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["semantic", "keyword", "hybrid"])
async def test_api_passes_all_filters_and_pagination(mode):
    service = AsyncMock()
    operation = getattr(service, f"search_{mode}")
    operation.return_value = []
    request = MemoryQueryRequest(
        query="database decision",
        search_mode=mode,
        session_id=uuid.uuid4(),
        tags=["project"],
        role="assistant",
        from_time=datetime.now(UTC) - timedelta(days=2),
        to_time=datetime.now(UTC),
        tag_filters=[TagFilter(key="kind", op="eq", value="decision")],
        limit=1,
        offset=2,
    )
    scope = MemoryScope(org_id=str(uuid.uuid4()), level="org")
    await MemoryQueryEngine(service).query(scope, request)
    kwargs = operation.call_args.kwargs
    for field in (
        "session_id",
        "tags",
        "tag_filters",
        "role",
        "from_time",
        "to_time",
        "limit",
        "offset",
    ):
        assert kwargs[field] == getattr(request, field)
    assert kwargs["scope"] == scope


@pytest.mark.asyncio
async def test_failure_does_not_silently_change_search_mode():
    service = AsyncMock()
    service.search_hybrid.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        await MemoryQueryEngine(service).query(
            MemoryScope(org_id=str(uuid.uuid4()), level="org"),
            MemoryQueryRequest(query="decision", tags=["project"], search_mode="hybrid"),
        )
    service.search_semantic.assert_not_called()


@pytest.mark.asyncio
async def test_no_text_query_filters_before_pagination():
    service = AsyncMock()
    service.list_filtered.return_value = []
    request = MemoryQueryRequest(tags=["project"], role="assistant", offset=5, limit=1)
    await MemoryQueryEngine(service).query(
        MemoryScope(org_id=str(uuid.uuid4()), level="org"), request
    )
    assert service.list_filtered.call_args.kwargs["offset"] == 5
    assert service.list_filtered.call_args.kwargs["tags"] == ["project"]


@pytest.mark.asyncio
async def test_context_query_filters_before_limit_without_query_text():
    from app.services.memory_query import MemoryQueryEngine as ContextEngine
    from app.services.memory_query import MemoryQueryRequest as ContextRequest

    service = AsyncMock()
    service.list_filtered.return_value = []
    request = ContextRequest(tags=["project"], role="assistant", limit=1, include_short_term=False)
    result = await ContextEngine(AsyncMock(), service).query(
        MemoryScope(org_id=str(uuid.uuid4()), level="org"), request
    )
    assert result.total_results == 0
    assert service.list_filtered.call_args.kwargs["limit"] == 1
    assert service.list_filtered.call_args.kwargs["tags"] == ["project"]
    service.search_by_time.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["semantic", "keyword", "hybrid", None])
async def test_real_storage_filters_before_limit_and_offset(db, mode):
    """Higher-ranked unrelated rows must not hide valid, lower-ranked matches."""
    from sqlalchemy import text

    from app.models import Embedding, Episode, Organization, Session
    from app.services.embeddings import set_embedding_provider_override
    from app.services.episodic import EpisodicMemory

    org, foreign_org = Organization(name="Filter regression"), Organization(name="Other tenant")
    db.add_all([org, foreign_org])
    await db.flush()
    session, other_session = Session(org_id=org.id), Session(org_id=org.id)
    db.add_all([session, other_session])
    await db.flush()
    now = datetime.now(UTC)

    async def add(**overrides):
        values = dict(
            org_id=org.id,
            session_id=session.id,
            content="database decision",
            role="assistant",
            tags=["project", "kind:decision"],
            metadata_={},
            created_at=now - timedelta(hours=2),
        )
        values.update(overrides)
        episode = Episode(**values)
        db.add(episode)
        await db.flush()
        db.add(
            Embedding(
                org_id=episode.org_id,
                episode_id=episode.id,
                content=episode.content,
                model="test",
                dimensions=3,
                vector=[1.0, 0.0, 0.0],
            )
        )
        await db.flush()
        return episode

    first = await add(created_at=now - timedelta(hours=1, minutes=30))
    second = await add()
    # Each distractor violates exactly one filter or deletion/tenant boundary.
    await add(session_id=other_session.id)
    await add(role="user")
    await add(tags=["elsewhere", "kind:decision"])
    await add(tags=["project", "kind:discussion"])
    await add(created_at=now)
    await add(created_at=now - timedelta(days=10))
    await add(deleted_at=now)
    await add(org_id=foreign_org.id, session_id=None)
    await db.execute(text("UPDATE episodes SET search_vector = to_tsvector('english', content)"))
    await db.commit()
    provider = AsyncMock()
    provider.generate_embedding.return_value = ([1.0, 0.0, 0.0], 3)
    set_embedding_provider_override(provider)
    try:
        engine = MemoryQueryEngine(EpisodicMemory(db))
        request = MemoryQueryRequest(
            query="database decision" if mode else None,
            search_mode=mode or "semantic",
            session_id=session.id,
            role="assistant",
            tags=["project"],
            tag_filters=[TagFilter(key="kind", op="eq", value="decision")],
            from_time=now - timedelta(hours=3),
            to_time=now - timedelta(hours=1),
            limit=1,
        )
        scope = MemoryScope(org_id=str(org.id), level="org")
        rows, _, _ = await engine.query(scope, request)
        assert [row.episode_id for row in rows] == [str(first.id)]
        rows, _, _ = await engine.query(scope, request.model_copy(update={"offset": 1}))
        assert [row.episode_id for row in rows] == [str(second.id)]
        rows, _, _ = await engine.query(scope, request.model_copy(update={"offset": 2}))
        assert rows == []
    finally:
        set_embedding_provider_override(None)
