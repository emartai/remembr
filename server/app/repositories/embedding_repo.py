"""Repository for embedding operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Embedding


class EmbeddingRepository:
    """Repository for managing embeddings."""

    @staticmethod
    async def store_embedding(
        session: AsyncSession,
        episode_id: uuid.UUID,
        org_id: uuid.UUID,
        embedding: list[float],
        model_name: str = "jina-embeddings-v3",
    ) -> Embedding:
        """
        Store an embedding for an episode.

        Args:
            session: Database session
            episode_id: Episode ID
            org_id: Organization ID
            embedding: 1024-dimensional embedding vector
            model_name: Name of the embedding model

        Returns:
            Created Embedding instance
        """
        # Check if embedding already exists
        result = await session.execute(select(Embedding).where(Embedding.episode_id == episode_id))
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing embedding
            existing.embedding = embedding
            existing.model_name = model_name
            await session.flush()
            return existing

        # Create new embedding
        emb = Embedding(
            episode_id=episode_id,
            org_id=org_id,
            embedding=embedding,
            model_name=model_name,
        )
        session.add(emb)
        await session.flush()
        return emb

    @staticmethod
    async def search_similar(
        session: AsyncSession,
        org_id: uuid.UUID,
        query_embedding: list[float],
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> list[tuple[uuid.UUID, float]]:
        """
        Search for similar episodes using cosine similarity.

        Args:
            session: Database session
            org_id: Organization ID for scoping
            query_embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of (episode_id, similarity_score) tuples, ordered by score desc
        """
        # Use pgvector's cosine distance operator (<=>)
        # Note: cosine distance = 1 - cosine similarity
        # So we convert: similarity = 1 - distance
        result = await session.execute(
            select(
                Embedding.episode_id,
                (1 - Embedding.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(Embedding.org_id == org_id)
            .order_by(Embedding.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        results = result.all()

        # Filter by threshold
        filtered = [
            (episode_id, float(similarity))
            for episode_id, similarity in results
            if similarity >= score_threshold
        ]

        return filtered

    @staticmethod
    async def get_embedding(
        session: AsyncSession,
        episode_id: uuid.UUID,
    ) -> Embedding | None:
        """
        Get embedding for an episode.

        Args:
            session: Database session
            episode_id: Episode ID

        Returns:
            Embedding instance or None if not found
        """
        result = await session.execute(select(Embedding).where(Embedding.episode_id == episode_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_embedding(
        session: AsyncSession,
        episode_id: uuid.UUID,
    ) -> bool:
        """
        Delete embedding for an episode.

        Args:
            session: Database session
            episode_id: Episode ID

        Returns:
            True if deleted, False if not found
        """
        result = await session.execute(select(Embedding).where(Embedding.episode_id == episode_id))
        embedding = result.scalar_one_or_none()

        if embedding:
            await session.delete(embedding)
            await session.flush()
            return True

        return False

    @staticmethod
    async def count_embeddings(
        session: AsyncSession,
        org_id: uuid.UUID,
    ) -> int:
        """
        Count embeddings for an organization.

        Args:
            session: Database session
            org_id: Organization ID

        Returns:
            Number of embeddings
        """
        from sqlalchemy import func

        result = await session.execute(
            select(func.count(Embedding.id)).where(Embedding.org_id == org_id)
        )
        return result.scalar_one()
