"""Local-provider embedding jobs for explicitly shared project memory."""

import math
import uuid

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.rls import set_org_context
from app.db.session import AsyncSessionLocal
from app.models.project_memory import ProjectMemory
from app.tasks.embeddings import _run_async


async def generate(memory_id: str, org_id: str, failed=False):
    from app.services.embeddings import get_embedding_provider

    async with AsyncSessionLocal() as db:
        await set_org_context(db, uuid.UUID(org_id))
        row = await db.scalar(
            select(ProjectMemory).where(
                ProjectMemory.id == uuid.UUID(memory_id), ProjectMemory.org_id == uuid.UUID(org_id)
            )
        )
        if not row or row.deleted_at:
            return
        if failed:
            row.embedding_status = "failed"
            row.embedding_error = "Embedding generation failed after retries"
        else:
            provider = get_embedding_provider()
            vector, dimensions = await provider.generate_embedding(row.content)
            if (
                len(vector) != dimensions
                or not vector
                or not all(math.isfinite(v) for v in vector)
                or not any(vector)
            ):
                raise ValueError("Invalid embedding")
            # Recheck after inference; a concurrent delete must not regain a vector.
            row = await db.scalar(
                select(ProjectMemory)
                .where(ProjectMemory.id == row.id, ProjectMemory.org_id == uuid.UUID(org_id))
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if row.deleted_at:
                return
            row.vector = vector
            row.embedding_model = provider.model
            row.embedding_status = "ready"
            row.embedding_error = None
        await db.commit()


@celery_app.task(bind=True, name="app.tasks.project_memory.embed", max_retries=3)
def embed_project_memory(self, memory_id: str, org_id: str):
    try:
        _run_async(generate(memory_id, org_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _run_async(generate(memory_id, org_id, failed=True))
        else:
            raise self.retry(exc=exc, countdown=2**self.request.retries)
