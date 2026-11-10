"""Real PostgreSQL authorization and lifecycle cases for shared memory."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.project_memory import ProjectMemory

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def shared(client, db, monkeypatch):
    from app.db.session import get_db
    from app.main import app
    from app.tasks.project_memory import embed_project_memory

    # The standard client fixture yields one shared session without committing.
    # This API intentionally relies on get_db's transaction boundary; reproduce it.
    async def transactional_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = transactional_db

    monkeypatch.setattr(embed_project_memory, "delay", lambda *args: None)
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "test-password-123",
            "org_name": "Shared memory test",
        },
    )
    assert registered.status_code == 201, registered.text
    owner = {"Authorization": "Bearer " + registered.json()["data"]["access_token"]}

    async def call(method, path, payload=None, headers=None):
        response = await client.request(
            method, "/api/v1/projects" + path, json=payload, headers=headers or owner
        )
        assert response.status_code < 300, response.text
        return response.json()["data"]

    project = await call("POST", "", {"name": "Product"})
    space = await call("POST", f"/{project['id']}/spaces", {"name": "Decisions"})
    a = await call("POST", "/principals", {"name": "Writer A"})
    b = await call("POST", "/principals", {"name": "Reader B"})
    await call(
        "PUT", f"/spaces/{space['id']}/grants/{a['id']}", {"can_read": True, "can_write": True}
    )
    await call("PUT", f"/spaces/{space['id']}/grants/{b['id']}", {"can_read": True})
    return {
        "client": client,
        "call": call,
        "owner": owner,
        "space": space["id"],
        "project": project["id"],
        "a": a,
        "b": b,
        "writer": {"X-API-Key": a["api_key"]},
        "reader": {"X-API-Key": b["api_key"]},
    }


async def save(s, **options):
    return await s["call"](
        "POST",
        f"/spaces/{s['space']}/memories",
        {
            "content": "We chose PostgreSQL for project memory.",
            "idempotency_key": "decision-1",
            "source_ref": "design/decision.md",
            **options,
        },
        s["writer"],
    )


@pytest.mark.asyncio
async def test_distinct_credentials_authorship_and_legacy_boundary(shared):
    s = shared
    memory = await save(s)
    assert memory["author_id"] == s["a"]["id"]
    read = await s["call"](
        "GET", f"/spaces/{s['space']}/memories/{memory['id']}", headers=s["reader"]
    )
    assert read["content"] == memory["content"]
    # These credentials cannot access any legacy session, export or private episode routes.
    for path in ("/memory/search", "/sessions"):
        response = (
            await s["client"].get("/api/v1" + path, headers=s["writer"])
            if path == "/sessions"
            else await s["client"].post("/api/v1" + path, headers=s["writer"], json={})
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_only_and_ungranted_cannot_write_discover_or_count(shared):
    s = shared
    memory = await save(s)
    base = f"/api/v1/projects/spaces/{s['space']}"
    denied = await s["client"].post(
        base + "/memories",
        headers=s["reader"],
        json={"content": "unauthorized write", "idempotency_key": "deny"},
    )
    assert denied.status_code == 404
    outsider = await s["call"]("POST", "/principals", {"name": "No grants"})
    headers = {"X-API-Key": outsider["api_key"]}
    assert await s["call"]("GET", "", headers=headers) == []
    for method, path, body in [
        ("POST", "/search", {}),
        ("GET", f"/memories/{memory['id']}", None),
        ("GET", f"/memories/{memory['id']}/status", None),
        ("DELETE", f"/memories/{memory['id']}", None),
    ]:
        response = await s["client"].request(method, base + path, headers=headers, json=body)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_space_list_exposes_only_effective_connection_permissions(shared):
    s = shared
    path = f"/{s['project']}/spaces"
    owner = await s["call"]("GET", path)
    reader = await s["call"]("GET", path, headers=s["reader"])
    assert owner[0]["permissions"] == {"can_read": True, "can_write": True, "can_delete": True}
    assert reader[0]["permissions"] == {"can_read": True, "can_write": False, "can_delete": False}
    await s["call"]("PUT", f"/spaces/{s['space']}/grants/{s['b']['id']}", {"can_write": True})
    writer = await s["call"]("GET", path, headers=s["reader"])
    assert writer[0]["permissions"] == {"can_read": False, "can_write": True, "can_delete": False}
    await s["call"]("PUT", f"/spaces/{s['space']}/grants/{s['b']['id']}", {})
    assert await s["call"]("GET", path, headers=s["reader"]) == []


@pytest.mark.asyncio
async def test_context_budget_pagination_does_not_hide_or_skip_memories(shared):
    s = shared
    expected = {
        (await save(s, content="Long synthetic pagination content", idempotency_key=str(i)))["id"]
        for i in range(3)
    }
    found, offset = [], 0
    for page in range(3):
        result = await s["call"](
            "POST",
            f"/spaces/{s['space']}/search",
            {"context_chars": 5, "offset": offset, "limit": 20},
            s["reader"],
        )
        assert len(result["results"]) == 1
        found.append(result["results"][0]["id"])
        assert result["has_more"] is (page < 2)
        assert result["next_offset"] == (offset + 1 if page < 2 else None)
        offset += 1
    assert len(set(found)) == 3 and set(found) == expected


@pytest.mark.asyncio
async def test_retry_payload_conflict_and_authenticated_identity(shared):
    s = shared
    first, second = await save(s), await save(s)
    assert first["id"] == second["id"]
    response = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/memories",
        headers=s["writer"],
        json={"content": "Different", "idempotency_key": "decision-1"},
    )
    assert response.status_code == 409
    response = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/memories",
        headers=s["writer"],
        json={"content": "Spoof", "idempotency_key": "spoof", "author_id": s["b"]["id"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_revocation_and_removed_grants_apply_even_to_retries(shared):
    s = shared
    memory = await save(s)
    path = f"/api/v1/projects/spaces/{s['space']}/search"
    # An HTTP cache must not bypass the next authorization check.
    headers = {**s["reader"], "Idempotency-Key": "same-header"}
    assert (await s["client"].post(path, headers=headers, json={})).status_code == 200
    await s["call"]("PUT", f"/spaces/{s['space']}/grants/{s['b']['id']}", {})
    assert (await s["client"].post(path, headers=headers, json={})).status_code == 404
    await s["call"]("DELETE", f"/principals/{s['a']['id']}")
    assert (
        await s["client"].get(
            f"/api/v1/projects/spaces/{s['space']}/memories/{memory['id']}", headers=s["writer"]
        )
    ).status_code == 401


@pytest.mark.asyncio
async def test_corrections_preserve_original_and_reject_stale_branch(shared):
    s = shared
    original = await save(s)
    correction = await save(
        s,
        content="We chose SQLite for the prototype.",
        idempotency_key="correction-1",
        supersedes_id=original["id"],
    )
    old = await s["call"](
        "GET", f"/spaces/{s['space']}/memories/{original['id']}", headers=s["reader"]
    )
    assert old["state"] == "superseded"
    assert old["content"] == original["content"]
    found = await s["call"]("POST", f"/spaces/{s['space']}/search", {}, s["reader"])
    assert [r["id"] for r in found["results"]] == [correction["id"]]
    response = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/memories",
        headers=s["writer"],
        json={"content": "stale", "idempotency_key": "stale", "supersedes_id": original["id"]},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_expiry_history_context_budget_and_delete_permissions(shared, db):
    s = shared
    memory = await save(s)
    row = await db.get(ProjectMemory, uuid.UUID(memory["id"]))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.commit()
    found = await s["call"]("POST", f"/spaces/{s['space']}/search", {}, s["reader"])
    assert found["results"] == []
    history = await s["call"](
        "POST",
        f"/spaces/{s['space']}/search",
        {"include_inactive": True, "context_chars": 10},
        s["reader"],
    )
    assert history["results"][0]["state"] == "expired"
    assert len(history["results"][0]["content"]) == 10 and history["truncated"]
    path = f"/api/v1/projects/spaces/{s['space']}/memories/{memory['id']}"
    assert (await s["client"].delete(path, headers=s["writer"])).status_code == 404
    await s["call"]("DELETE", f"/spaces/{s['space']}/memories/{memory['id']}")
    assert (await s["client"].get(path, headers=s["reader"])).status_code == 404
    remaining = await db.scalar(
        select(ProjectMemory).where(ProjectMemory.id == uuid.UUID(memory["id"]))
    )
    assert remaining.content == "" and remaining.vector is None


@pytest.mark.asyncio
async def test_search_modes_processing_and_source_metadata(shared, db, monkeypatch):
    s = shared
    memory = await save(s)
    row = await db.get(ProjectMemory, uuid.UUID(memory["id"]))
    row.vector, row.embedding_model, row.embedding_status = [1, 0, 0], "test-local", "ready"
    await db.commit()

    class Provider:
        model = "test-local"

        async def generate_embedding(self, text):
            return [1, 0, 0], 3

    monkeypatch.setattr("app.services.embeddings.get_embedding_provider", lambda: Provider())
    for mode in ("keyword", "semantic", "hybrid"):
        result = await s["call"](
            "POST",
            f"/spaces/{s['space']}/search",
            {"query": "PostgreSQL", "mode": mode},
            s["reader"],
        )
        assert result["results"][0]["id"] == memory["id"]
        assert result["results"][0]["source_ref"] == "design/decision.md"
        assert result["mode"] == mode and "probabilities" in result["score_explanation"]
    status = await s["call"](
        "GET", f"/spaces/{s['space']}/memories/{memory['id']}/status", headers=s["reader"]
    )
    assert status["embedding_status"] == "ready"


@pytest.mark.asyncio
async def test_cross_organization_and_existing_private_memory_stay_isolated(shared):
    s = shared
    # A legacy memory is not moved or mirrored into shared spaces.
    await s["client"].post(
        "/api/v1/memory", headers=s["owner"], json={"role": "user", "content": "Private marker"}
    )
    result = await s["call"]("POST", f"/spaces/{s['space']}/search", {}, s["reader"])
    assert result["results"] == []
    other = await s["client"].post(
        "/api/v1/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "another-password",
            "org_name": "Other",
        },
    )
    foreign = {"Authorization": "Bearer " + other.json()["data"]["access_token"]}
    response = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/search", json={}, headers=foreign
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_five_runtime_credentials_share_corrections_and_revoke_independently(shared):
    """Model account logins are external; verify five independent Remembr identities."""
    s = shared
    principals = [s["a"], s["b"]]
    for label in ("Claude profile 2", "Codex profile 1", "Codex profile 2"):
        principal = await s["call"]("POST", "/principals", {"name": label})
        principals.append(principal)
    for principal in principals:
        await s["call"](
            "PUT",
            f"/spaces/{s['space']}/grants/{principal['id']}",
            {"can_read": True, "can_write": True},
        )
    assert len({p["api_key"] for p in principals}) == 5
    original = await save(s)
    headers = [{"X-API-Key": p["api_key"]} for p in principals]
    corrected = await s["call"](
        "POST",
        f"/spaces/{s['space']}/memories",
        {
            "content": "Correction: use PostgreSQL with pgvector.",
            "idempotency_key": "multi-profile-correction",
            "supersedes_id": original["id"],
        },
        headers[2],
    )
    assert corrected["author_id"] == principals[2]["id"]
    for header in headers:
        result = await s["call"]("POST", f"/spaces/{s['space']}/search", {}, header)
        assert [r["id"] for r in result["results"]] == [corrected["id"]]
    await s["call"]("DELETE", f"/principals/{principals[0]['id']}")
    denied = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/search", json={}, headers=headers[0]
    )
    assert denied.status_code == 401
    for header in headers[1:]:
        result = await s["call"](
            "GET", f"/spaces/{s['space']}/memories/{corrected['id']}", headers=header
        )
        assert result["author_id"] == principals[2]["id"]


@pytest.mark.asyncio
async def test_retry_preserves_identity_and_recovers_provider_failure(shared, db, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.tasks import project_memory as task

    s = shared
    memory = await save(s)
    org_id = str((await db.get(ProjectMemory, uuid.UUID(memory["id"]))).org_id)
    monkeypatch.setattr(
        task, "AsyncSessionLocal", async_sessionmaker(db.bind, expire_on_commit=False)
    )

    class Provider:
        model = "recovery-test"
        unavailable = True

        async def generate_embedding(self, text):
            if self.unavailable:
                raise ConnectionError("Local provider unavailable")
            return [1.0, 0.0, 0.0], 3

    provider = Provider()
    monkeypatch.setattr("app.services.embeddings.get_embedding_provider", lambda: provider)
    with pytest.raises(ConnectionError):
        await task.generate(memory["id"], org_id)
    await task.generate(memory["id"], org_id, failed=True)
    db.expire_all()
    queued = []
    monkeypatch.setattr(task.embed_project_memory, "delay", lambda *args: queued.append(args))
    endpoint = f"/spaces/{s['space']}/memories/{memory['id']}/retry-embedding"
    response = await s["call"]("POST", endpoint, {}, s["writer"])
    assert response["queued"] and response["embedding_status"] == "pending"
    assert "content" not in response and len(queued) == 1
    assert not (await s["call"]("POST", endpoint, {}, s["writer"]))["queued"]
    provider.unavailable = False
    await task.generate(memory["id"], org_id)
    # A delayed failure notification from an earlier duplicate must not demote ready.
    await task.generate(memory["id"], org_id, failed=True)
    db.expire_all()
    restored = await s["call"]("GET", f"/spaces/{s['space']}/memories/{memory['id']}")
    assert restored["embedding_status"] == "ready"
    assert restored["author_id"] == memory["author_id"]
    assert restored["content"] == memory["content"]
    assert not (await s["call"]("POST", endpoint, {}, s["writer"]))["queued"]


@pytest.mark.asyncio
async def test_retry_queue_outage_pending_requeue_and_permission_boundaries(
    shared, db, monkeypatch
):
    from app.tasks.project_memory import embed_project_memory

    s = shared
    memory = await save(s)
    endpoint = f"/spaces/{s['space']}/memories/{memory['id']}/retry-embedding"
    full = "/api/v1/projects" + endpoint
    assert (await s["client"].post(full, json={}, headers=s["reader"])).status_code == 404
    outsider = await s["call"]("POST", "/principals", {"name": "Ungrantable outsider"})
    assert (
        await s["client"].post(full, json={}, headers={"X-API-Key": outsider["api_key"]})
    ).status_code == 404

    def queue_down(*args):
        raise ConnectionError("Broker unavailable")

    monkeypatch.setattr(embed_project_memory, "delay", queue_down)
    result = await s["call"]("POST", endpoint, {"retry_pending": True}, s["writer"])
    assert not result["queued"] and result["embedding_status"] == "failed"
    queued = []
    monkeypatch.setattr(embed_project_memory, "delay", lambda *args: queued.append(args))
    await s["call"]("PUT", f"/spaces/{s['space']}/grants/{s['a']['id']}", {"can_write": True})
    result = await s["call"]("POST", endpoint, {}, s["writer"])
    assert result["queued"] and "content" not in result
    assert len(queued) == 1
    # An explicit pending retry is available after a worker/process outage.
    assert (await s["call"]("POST", endpoint, {"retry_pending": True}, s["writer"]))["queued"]
    await s["call"]("DELETE", f"/spaces/{s['space']}/memories/{memory['id']}")
    assert (await s["client"].post(full, json={}, headers=s["writer"])).status_code == 404


@pytest.mark.asyncio
async def test_delete_during_embedding_cannot_restore_content_or_vector(shared, db, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.tasks import project_memory as task

    s = shared
    memory = await save(s)
    org_id = str((await db.get(ProjectMemory, uuid.UUID(memory["id"]))).org_id)
    monkeypatch.setattr(
        task, "AsyncSessionLocal", async_sessionmaker(db.bind, expire_on_commit=False)
    )

    class Provider:
        model = "delete-race-test"

        async def generate_embedding(self, text):
            await s["call"]("DELETE", f"/spaces/{s['space']}/memories/{memory['id']}")
            return [1.0, 0.0, 0.0], 3

    monkeypatch.setattr("app.services.embeddings.get_embedding_provider", lambda: Provider())
    await task.generate(memory["id"], org_id)
    row = await db.get(ProjectMemory, uuid.UUID(memory["id"]), populate_existing=True)
    assert row.deleted_at and row.content == "" and row.vector is None


def install_ranking_provider(monkeypatch):
    class Provider:
        model = "ranking-test"

        async def generate_embedding(self, text):
            return [1.0, 0.0, 0.0], 3

    monkeypatch.setattr("app.services.embeddings.get_embedding_provider", lambda: Provider())


@pytest.mark.asyncio
async def test_experimental_ranker_filters_sources_and_preserves_budget_pagination(
    shared, db, monkeypatch
):
    from app.models import Organization

    s = shared
    install_ranking_provider(monkeypatch)
    visible = []
    for index in range(3):
        memory = await save(
            s, content=f"PostgreSQL database decision {index}", idempotency_key=f"rank-{index}"
        )
        row = await db.get(ProjectMemory, uuid.UUID(memory["id"]))
        row.vector, row.embedding_model, row.embedding_status = (
            [1.0, 0.0, 0.0],
            "ranking-test",
            "ready",
        )
        visible.append(memory["id"])
    hidden = await save(
        s, content="PostgreSQL incompatible private marker", idempotency_key="rank-incompatible"
    )
    row = await db.get(ProjectMemory, uuid.UUID(hidden["id"]))
    row.vector, row.embedding_model, row.embedding_status = [1.0, 0.0], "other-model", "ready"
    foreign = Organization(name="Foreign ranker tenant")
    db.add(foreign)
    await db.flush()
    db.add(
        ProjectMemory(
            org_id=foreign.id,
            space_id=uuid.UUID(s["space"]),
            author_id=uuid.uuid4(),
            author_kind="principal",
            content="PostgreSQL foreign private marker",
            idempotency_key="foreign-rank",
            payload_hash="0" * 64,
            vector=[1.0, 0.0, 0.0],
            embedding_model="ranking-test",
            embedding_status="ready",
        )
    )
    await db.commit()
    found, offset = [], 0
    while True:
        response = await s["call"](
            "POST",
            f"/spaces/{s['space']}/search",
            {
                "query": "PostgreSQL",
                "mode": "hybrid",
                "ranking": "rrf_mmr",
                "limit": 2,
                "offset": offset,
                "context_chars": 10,
            },
            s["reader"],
        )
        assert response["ranking"] == "rrf_mmr"
        assert response["context_chars_used"] <= 10
        assert all(r["retrieval_reason"] == "hybrid_rrf_mmr" for r in response["results"])
        assert "not probabilities" in response["score_explanation"]
        found.extend(r["id"] for r in response["results"])
        if not response["has_more"]:
            break
        assert response["next_offset"] > offset
        offset = response["next_offset"]
    assert sorted(found) == sorted(visible)
    outsider = await s["call"]("POST", "/principals", {"name": "No ranking access"})
    denied = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/search",
        json={"query": "PostgreSQL", "ranking": "rrf_mmr"},
        headers={"X-API-Key": outsider["api_key"]},
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_experimental_ranker_caps_candidates_without_affecting_weighted_search(
    shared, db, monkeypatch
):
    s = shared
    install_ranking_provider(monkeypatch)
    await save(s)
    # Fetch the organization from a real saved memory; author IDs are independent.
    original = await db.scalar(
        select(ProjectMemory).where(ProjectMemory.space_id == uuid.UUID(s["space"]))
    )
    org_id = original.org_id
    for index in range(201):
        db.add(
            ProjectMemory(
                org_id=org_id,
                space_id=uuid.UUID(s["space"]),
                author_id=uuid.UUID(s["a"]["id"]),
                author_kind="principal",
                content=f"database {index}",
                idempotency_key=f"cap-{index}",
                payload_hash="0" * 64,
                vector=[1.0, 0.0, 0.0],
                embedding_model="ranking-test",
                embedding_status="ready",
            )
        )
    await db.commit()
    response = await s["client"].post(
        f"/api/v1/projects/spaces/{s['space']}/search",
        json={"query": "database", "ranking": "rrf_mmr"},
        headers=s["reader"],
    )
    assert response.status_code == 422
    assert "200" in response.text
    weighted = await s["call"](
        "POST", f"/spaces/{s['space']}/search", {"query": "database", "limit": 2}, s["reader"]
    )
    assert weighted["ranking"] == "weighted" and len(weighted["results"]) == 2


@pytest.mark.asyncio
async def test_experimental_ranking_requires_hybrid_query(shared):
    s = shared
    for body in ({"ranking": "rrf_mmr"}, {"query": "q", "ranking": "rrf_mmr", "mode": "keyword"}):
        response = await s["client"].post(
            f"/api/v1/projects/spaces/{s['space']}/search", json=body, headers=s["reader"]
        )
        assert response.status_code == 422
