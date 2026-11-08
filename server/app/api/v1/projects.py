"""Project memory API with explicit per-principal grants and append-only corrections."""

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Float, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import success
from app.db.rls import set_org_context
from app.db.session import get_db
from app.middleware.context import RequestContext, get_request_context
from app.models.project_memory import (
    MemorySpace,
    Project,
    ProjectMemory,
    SpaceGrant,
    SpacePrincipal,
)
from app.services.api_keys import hash_api_key

router = APIRouter(prefix="/projects", tags=["project-memory"])


@dataclass
class Actor:
    id: uuid.UUID
    org_id: uuid.UUID
    kind: str


async def actor(
    ctx: RequestContext | None = Depends(get_request_context),
    key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Actor:
    if key and key.startswith("rmsp_"):
        if ctx:
            raise HTTPException(400, "Use one credential per request")
        principal = await db.scalar(
            select(SpacePrincipal).where(
                SpacePrincipal.key_hash == hash_api_key(key),
                SpacePrincipal.revoked_at.is_(None),
            )
        )
        if not principal:
            raise HTTPException(401, "Invalid or revoked space credential")
        result = Actor(principal.id, principal.org_id, "principal")
    elif ctx and ctx.auth_method == "jwt" and ctx.user_id:
        result = Actor(ctx.user_id, ctx.org_id, "user")
    else:
        raise HTTPException(401, "Use a space credential or user access token")
    await set_org_context(db, result.org_id)
    return result


async def owned_project(db, who, project_id):
    project = (
        await db.scalar(
            select(Project).where(
                Project.id == project_id, Project.org_id == who.org_id, Project.owner_id == who.id
            )
        )
        if who.kind == "user"
        else None
    )
    if not project:
        raise HTTPException(404, "Project not found")
    return project


async def permitted_space(db, who, space_id, permission="read"):
    space = await db.scalar(
        select(MemorySpace).where(MemorySpace.id == space_id, MemorySpace.org_id == who.org_id)
    )
    if space:
        project = await db.scalar(
            select(Project).where(Project.id == space.project_id, Project.org_id == who.org_id)
        )
        if project and who.kind == "user" and project.owner_id == who.id:
            return space
        grant = await db.get(SpaceGrant, (space.id, who.id)) if who.kind == "principal" else None
        if grant and getattr(grant, f"can_{permission}", False):
            return space
    # Do not reveal space existence to an unauthorized connection.
    raise HTTPException(404, "Space not found")


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Named(Payload):
    name: str = Field(min_length=1, max_length=160)


class GrantInput(Payload):
    can_read: bool = False
    can_write: bool = False
    can_delete: bool = False


class StoreInput(Payload):
    content: str = Field(min_length=1, max_length=32000)
    source_ref: str | None = Field(default=None, max_length=2000)
    run_id: str | None = Field(default=None, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=160)
    supersedes_id: uuid.UUID | None = None
    expires_at: AwareDatetime | None = None


class SearchInput(Payload):
    query: str = Field(default="", max_length=2000)
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)
    context_chars: int = Field(default=12000, ge=1, le=64000)
    include_inactive: bool = False

    @model_validator(mode="after")
    def validate_history(self):
        if self.include_inactive and self.query:
            raise ValueError("History browsing requires an empty query")
        return self


def memory_dict(row):
    now = datetime.now(UTC)
    state = (
        "deleted"
        if row.deleted_at
        else "superseded"
        if row.superseded_at
        else "expired"
        if row.expires_at and row.expires_at <= now
        else "active"
    )
    return {
        "id": str(row.id),
        "space_id": str(row.space_id),
        "content": row.content,
        "author_id": str(row.author_id),
        "author_kind": row.author_kind,
        "source_ref": row.source_ref,
        "run_id": row.run_id,
        "state": state,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "supersedes_id": str(row.supersedes_id) if row.supersedes_id else None,
        "embedding_status": row.embedding_status,
        "embedding_error": row.embedding_error,
    }


@router.post("", status_code=201)
async def create_project(payload: Named, request: Request, who=Depends(actor), db=Depends(get_db)):
    if who.kind != "user":
        raise HTTPException(403, "User access token required")
    project = Project(org_id=who.org_id, owner_id=who.id, name=payload.name)
    db.add(project)
    await db.flush()
    await db.commit()
    return success(
        {"id": str(project.id), "name": project.name}, request_id=request.state.request_id
    )


@router.get("")
async def list_projects(request: Request, who=Depends(actor), db=Depends(get_db)):
    query = select(Project).where(Project.org_id == who.org_id)
    if who.kind == "user":
        query = query.where(Project.owner_id == who.id)
    else:
        query = query.where(
            Project.id.in_(
                select(MemorySpace.project_id)
                .join(SpaceGrant)
                .where(
                    SpaceGrant.principal_id == who.id,
                    or_(SpaceGrant.can_read, SpaceGrant.can_write, SpaceGrant.can_delete),
                )
            )
        )
    rows = (await db.scalars(query.order_by(Project.created_at, Project.id).limit(100))).all()
    return success(
        [{"id": str(r.id), "name": r.name} for r in rows], request_id=request.state.request_id
    )


@router.post("/principals", status_code=201)
async def create_principal(
    payload: Named, request: Request, who=Depends(actor), db=Depends(get_db)
):
    if who.kind != "user":
        raise HTTPException(403, "User access token required")
    raw = "rmsp_" + secrets.token_urlsafe(32)
    principal = SpacePrincipal(
        org_id=who.org_id, issuer_id=who.id, name=payload.name, key_hash=hash_api_key(raw)
    )
    db.add(principal)
    await db.flush()
    await db.commit()
    return success(
        {"id": str(principal.id), "name": principal.name, "api_key": raw},
        request_id=request.state.request_id,
    )


@router.delete("/principals/{principal_id}")
async def revoke_principal(
    principal_id: uuid.UUID, request: Request, who=Depends(actor), db=Depends(get_db)
):
    principal = (
        await db.scalar(
            select(SpacePrincipal).where(
                SpacePrincipal.id == principal_id,
                SpacePrincipal.org_id == who.org_id,
                SpacePrincipal.issuer_id == who.id,
            )
        )
        if who.kind == "user"
        else None
    )
    if not principal:
        raise HTTPException(404, "Principal not found")
    principal.revoked_at = datetime.now(UTC)
    await db.commit()
    return success({"revoked": True}, request_id=request.state.request_id)


@router.post("/{project_id}/spaces", status_code=201)
async def create_space(
    project_id: uuid.UUID, payload: Named, request: Request, who=Depends(actor), db=Depends(get_db)
):
    await owned_project(db, who, project_id)
    space = MemorySpace(org_id=who.org_id, project_id=project_id, name=payload.name)
    db.add(space)
    await db.flush()
    await db.commit()
    return success(
        {"id": str(space.id), "name": space.name, "project_id": str(project_id)},
        request_id=request.state.request_id,
    )


@router.get("/{project_id}/spaces")
async def list_spaces(
    project_id: uuid.UUID, request: Request, who=Depends(actor), db=Depends(get_db)
):
    query = select(MemorySpace).where(
        MemorySpace.project_id == project_id, MemorySpace.org_id == who.org_id
    )
    if who.kind == "user":
        await owned_project(db, who, project_id)
    else:
        query = query.join(SpaceGrant).where(
            SpaceGrant.principal_id == who.id,
            or_(SpaceGrant.can_read, SpaceGrant.can_write, SpaceGrant.can_delete),
        )
    rows = (
        await db.scalars(query.order_by(MemorySpace.created_at, MemorySpace.id).limit(100))
    ).all()
    grants = (
        {
            grant.space_id: grant
            for grant in (
                await db.scalars(
                    select(SpaceGrant).where(
                        SpaceGrant.principal_id == who.id,
                        SpaceGrant.space_id.in_([row.id for row in rows]),
                    )
                )
            ).all()
        }
        if who.kind == "principal" and rows
        else {}
    )
    return success(
        [
            {
                "id": str(r.id),
                "name": r.name,
                "permissions": {
                    "can_read": who.kind == "user" or grants[r.id].can_read,
                    "can_write": who.kind == "user" or grants[r.id].can_write,
                    "can_delete": who.kind == "user" or grants[r.id].can_delete,
                },
            }
            for r in rows
        ],
        request_id=request.state.request_id,
    )


@router.put("/spaces/{space_id}/grants/{principal_id}")
async def set_grant(
    space_id: uuid.UUID,
    principal_id: uuid.UUID,
    payload: GrantInput,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    space = await permitted_space(db, who, space_id, "manage")
    await owned_project(db, who, space.project_id)
    principal = await db.scalar(
        select(SpacePrincipal).where(
            SpacePrincipal.id == principal_id,
            SpacePrincipal.org_id == who.org_id,
            SpacePrincipal.issuer_id == who.id,
            SpacePrincipal.revoked_at.is_(None),
        )
    )
    if not principal:
        raise HTTPException(404, "Principal not found")
    grant = await db.get(SpaceGrant, (space_id, principal_id))
    if not grant:
        grant = SpaceGrant(space_id=space_id, principal_id=principal_id)
        db.add(grant)
    for name, value in payload.model_dump().items():
        setattr(grant, name, value)
    await db.commit()
    return success(payload.model_dump(), request_id=request.state.request_id)


@router.post("/spaces/{space_id}/memories", status_code=201)
async def store_memory(
    space_id: uuid.UUID,
    payload: StoreInput,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    await permitted_space(db, who, space_id, "write")
    # Serialize retries/corrections for this space before checking unique constraints.
    await db.scalar(select(MemorySpace).where(MemorySpace.id == space_id).with_for_update())
    digest = hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    existing = await db.scalar(
        select(ProjectMemory).where(
            ProjectMemory.space_id == space_id,
            ProjectMemory.org_id == who.org_id,
            ProjectMemory.author_id == who.id,
            ProjectMemory.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        if existing.payload_hash != digest:
            raise HTTPException(409, "Idempotency key was used for different content")
        await db.commit()  # Release the per-space retry lock before sending the response.
        return success(memory_dict(existing), request_id=request.state.request_id)
    if payload.expires_at and payload.expires_at <= datetime.now(UTC):
        raise HTTPException(422, "Expiry must be in the future")
    if payload.supersedes_id:
        # Corrections expose the referenced content, so both read and write are required.
        await permitted_space(db, who, space_id, "read")
        original = await db.scalar(
            select(ProjectMemory)
            .where(
                ProjectMemory.id == payload.supersedes_id,
                ProjectMemory.space_id == space_id,
                ProjectMemory.org_id == who.org_id,
            )
            .with_for_update()
        )
        if not original or original.deleted_at:
            raise HTTPException(404, "Memory not found")
        if original.superseded_at:
            raise HTTPException(409, "Memory already corrected; refresh before correcting")
        original.superseded_at = datetime.now(UTC)
    row = ProjectMemory(
        org_id=who.org_id,
        space_id=space_id,
        author_id=who.id,
        author_kind=who.kind,
        payload_hash=digest,
        **payload.model_dump(),
    )
    db.add(row)
    await db.flush()
    await db.commit()  # The worker must see the committed memory.
    from app.tasks.project_memory import embed_project_memory

    try:
        embed_project_memory.delay(str(row.id), str(who.org_id))
    except Exception:
        await set_org_context(db, who.org_id)
        row.embedding_status = "failed"
        row.embedding_error = (
            "Embedding task could not be queued; save again with a new key to retry"
        )
        await db.commit()
    return success(memory_dict(row), request_id=request.state.request_id)


@router.get("/spaces/{space_id}/memories/{memory_id}")
async def get_memory(
    space_id: uuid.UUID,
    memory_id: uuid.UUID,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    await permitted_space(db, who, space_id)
    row = await db.scalar(
        select(ProjectMemory).where(
            ProjectMemory.id == memory_id,
            ProjectMemory.space_id == space_id,
            ProjectMemory.org_id == who.org_id,
            ProjectMemory.deleted_at.is_(None),
        )
    )
    if not row:
        raise HTTPException(404, "Memory not found")
    return success(memory_dict(row), request_id=request.state.request_id)


@router.get("/spaces/{space_id}/memories/{memory_id}/status")
async def memory_status(
    space_id: uuid.UUID,
    memory_id: uuid.UUID,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    result = await get_memory(space_id, memory_id, request, who, db)
    data = result.data
    return success(
        {k: data[k] for k in ("id", "state", "embedding_status", "embedding_error")},
        request_id=request.state.request_id,
    )


@router.delete("/spaces/{space_id}/memories/{memory_id}")
async def delete_memory(
    space_id: uuid.UUID,
    memory_id: uuid.UUID,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    await permitted_space(db, who, space_id, "delete")
    row = await db.scalar(
        select(ProjectMemory)
        .where(
            ProjectMemory.id == memory_id,
            ProjectMemory.space_id == space_id,
            ProjectMemory.org_id == who.org_id,
            ProjectMemory.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(404, "Memory not found")
    row.deleted_at = datetime.now(UTC)
    row.content = ""  # Remove content and vectors; retain only the revision tombstone.
    row.vector = None
    row.source_ref = None
    row.run_id = None
    await db.commit()
    return success({"deleted": True, "id": str(memory_id)}, request_id=request.state.request_id)


@router.post("/spaces/{space_id}/search")
async def search_memory(
    space_id: uuid.UUID,
    payload: SearchInput,
    request: Request,
    who=Depends(actor),
    db=Depends(get_db),
):
    await permitted_space(db, who, space_id)
    conditions = [
        ProjectMemory.space_id == space_id,
        ProjectMemory.org_id == who.org_id,
        ProjectMemory.deleted_at.is_(None),
    ]
    if not payload.include_inactive:
        conditions += [
            ProjectMemory.superseded_at.is_(None),
            or_(ProjectMemory.expires_at.is_(None), ProjectMemory.expires_at > func.now()),
        ]
    score = None
    selected_mode = payload.mode if payload.query else "recent"
    if payload.query:
        ts_query = func.plainto_tsquery("english", payload.query)
        document = func.to_tsvector("english", ProjectMemory.content)
        keyword = func.ts_rank_cd(document, ts_query)
        if payload.mode == "keyword":
            conditions.append(document.op("@@")(ts_query))
            score = keyword
        else:
            from app.services.embeddings import get_embedding_provider
            from app.services.embeddings.base import embed_query

            provider = get_embedding_provider()
            try:
                vector, dimensions = await embed_query(provider, payload.query)
            except Exception as exc:
                raise HTTPException(
                    503, "Embedding provider unavailable; use keyword search"
                ) from exc
            compatible = (ProjectMemory.embedding_model == provider.model) & (
                func.vector_dims(ProjectMemory.vector) == dimensions
            )
            semantic = case(
                (compatible, 1 - ProjectMemory.vector.cosine_distance(vector)), else_=0.0
            )
            if payload.mode == "semantic":
                conditions += [compatible, ProjectMemory.embedding_status == "ready"]
                score = semantic
            else:
                score = 0.7 * semantic + 0.3 * (keyword / (1 + keyword))
    query = select(
        ProjectMemory,
        score.label("score") if score is not None else cast(0.0, Float).label("score"),
    ).where(*conditions)
    if score is not None:
        query = query.order_by(score.desc())
    query = (
        query.order_by(ProjectMemory.created_at.desc(), ProjectMemory.id)
        .offset(payload.offset)
        .limit(payload.limit + 1)
    )
    rows = (await db.execute(query)).all()
    has_more = len(rows) > payload.limit
    results, remaining, truncated = [], payload.context_chars, has_more
    for row, value in rows[: payload.limit]:
        if remaining <= 0:
            truncated = True
            break
        item = memory_dict(row)
        item["content_truncated"] = len(row.content) > remaining
        item["content"] = row.content[:remaining]
        remaining -= len(item["content"])
        truncated |= item["content_truncated"]
        item["score"] = float(value or 0)
        item["retrieval_reason"] = selected_mode
        results.append(item)
    # A context budget can end a page before the row limit. Advance by rows
    # actually returned so clients neither skip records nor hide the next page.
    has_more = len(rows) > len(results)
    return success(
        {
            "results": results,
            "mode": selected_mode,
            "space_id": str(space_id),
            "offset": payload.offset,
            "has_more": has_more,
            "next_offset": payload.offset + len(results) if has_more else None,
            "truncated": truncated,
            "context_chars_used": payload.context_chars - remaining,
            "include_inactive": payload.include_inactive,
            "score_explanation": (
                "keyword: PostgreSQL ts_rank_cd; semantic: cosine similarity; "
                "hybrid: 0.7 cosine + 0.3 normalized keyword. Scores are not probabilities."
            ),
        },
        request_id=request.state.request_id,
    )
