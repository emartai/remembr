"""Real PostgreSQL authorization and lifecycle cases for shared memory."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.project_memory import ProjectMemory


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
