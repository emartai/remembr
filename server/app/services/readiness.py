"""Bounded checks for a usable memory pipeline, separate from HTTP liveness."""

from __future__ import annotations

import asyncio
import math
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from loguru import logger
from sqlalchemy import text


async def check_database() -> None:
    from app.db.session import engine

    server_dir = Path(__file__).resolve().parents[2]
    config = Config(str(server_dir / "alembic.ini"))
    config.set_main_option("script_location", str(server_dir / "alembic"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    async with engine.connect() as conn:
        revisions = set(
            (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalars()
        )
        if revisions != expected:
            raise RuntimeError("Database migrations are not current")
        vector = await conn.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")
        )
        if not vector:
            raise RuntimeError("pgvector extension is missing")


async def check_redis() -> None:
    from app.db.redis import get_redis_client

    await get_redis_client().ping()


async def check_worker() -> None:
    from app.celery_app import celery_app

    registered = await asyncio.to_thread(celery_app.control.inspect(timeout=2.0).registered)
    required = {
        "app.tasks.embeddings.generate_embedding_for_episode",
        "app.tasks.project_memory.embed",
    }
    if not registered or not any(required.issubset(tasks) for tasks in registered.values()):
        raise RuntimeError("No worker with both embedding tasks registered responded")


async def check_embeddings() -> None:
    from app.services.embeddings import get_embedding_provider

    vector, dimensions = await get_embedding_provider().generate_embedding("Remembr readiness")
    if not vector or len(vector) != dimensions or not all(math.isfinite(v) for v in vector):
        raise RuntimeError("Embedding provider returned an invalid vector")


async def get_readiness() -> dict[str, str]:
    async def check(name, operation, timeout=10.0):
        try:
            await asyncio.wait_for(operation(), timeout=timeout)
            return name, "healthy"
        except Exception as error:
            # Public output contains component names, not credentials or provider errors.
            logger.warning(
                "Readiness check failed", component=name, error_type=type(error).__name__
            )
            return name, "unhealthy"

    return dict(
        await asyncio.gather(
            check("database", check_database),
            check("redis", check_redis),
            check("worker", check_worker),
            check("embeddings", check_embeddings, timeout=30.0),
        )
    )
