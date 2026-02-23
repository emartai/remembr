"""Episodic memory service for logging and retrieval."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import AsyncSessionLocal
from app.models import Embedding, Episode
from app.repositories import episode_repo
from app.services.embedding_service import EmbeddingService
from app.services.scoping import MemoryScope


class EpisodicMemory:
    """High-level episodic memory service with async embedding enrichment."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.session_factory = session_factory or AsyncSessionLocal

    async def log(
        self,
        scope: MemoryScope,
        role: str,
        content: str,
        tags: list[str] | None = None,
        session_id: str | uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Episode:
        """Log an episode first, then asynchronously generate and store embedding."""
        episode = await episode_repo.log_episode(
            db=self.db,
            scope=scope,
            role=role,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
            session_id=session_id,
        )

        asyncio.create_task(self._generate_and_store_embedding(episode.id, content))
        return episode

    async def search_by_tags(
        self,
        scope: MemoryScope,
        tags: list[str],
        limit: int = 20,
    ) -> list[Episode]:
        """Return episodes whose tags overlap the provided set."""
        return await episode_repo.list_episodes(
            db=self.db,
            scope=scope,
            tags=tags,
            limit=limit,
        )

    async def search_by_time(
        self,
        scope: MemoryScope,
        from_time: datetime | None,
        to_time: datetime | None,
        limit: int = 50,
    ) -> list[Episode]:
        """Return episodes constrained to a time range."""
        return await episode_repo.list_episodes(
            db=self.db,
            scope=scope,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
        )

    async def get_session_history(
        self,
        scope: MemoryScope,
        session_id: str | uuid.UUID,
        limit: int = 100,
    ) -> list[Episode]:
        """Return recent session episodes in descending creation order."""
        return await episode_repo.list_episodes(
            db=self.db,
            scope=scope,
            session_id=session_id,
            limit=limit,
        )

    async def replay_session(
        self,
        scope: MemoryScope,
        session_id: str | uuid.UUID,
    ) -> list[Episode]:
        """Return full session history ordered oldest-to-newest."""
        history = await episode_repo.list_episodes(
            db=self.db,
            scope=scope,
            session_id=session_id,
            limit=10_000,
        )
        return sorted(history, key=lambda ep: ep.created_at)

    async def delete(self, scope: MemoryScope, episode_id: str | uuid.UUID) -> None:
        """Delete an episode in scope."""
        await episode_repo.delete_episode(
            db=self.db,
            episode_id=episode_id,
            scope=scope,
        )

    async def _generate_and_store_embedding(
        self,
        episode_id: uuid.UUID,
        content: str,
    ) -> None:
        """Background task: create embedding and persist to embeddings table."""
        try:
            vector, dimensions = await self.embedding_service.generate_embedding(content)
        except Exception:
            logger.exception("Failed to generate episode embedding", episode_id=str(episode_id))
            return

        try:
            async with self.session_factory() as background_db:
                episode = await background_db.get(Episode, episode_id)
                if episode is None:
                    logger.warning(
                        "Skipping embedding save: episode not found",
                        episode_id=str(episode_id),
                    )
                    return

                embedding = Embedding(
                    org_id=episode.org_id,
                    episode_id=episode.id,
                    content=content,
                    model=self.embedding_service.model,
                    dimensions=dimensions,
                    vector=vector,
                )
                background_db.add(embedding)
                await background_db.commit()

                logger.debug(
                    "Episode embedding stored",
                    episode_id=str(episode_id),
                    dimensions=dimensions,
                )
        except Exception:
            logger.exception("Failed to persist episode embedding", episode_id=str(episode_id))
