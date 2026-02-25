"""Embedding repository for vector operations."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Embedding


class EmbeddingRepository:
    """Repository for embedding operations including similarity search."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        org_id: uuid.UUID,
        content: str,
        vector: list[float],
        model: str,
        dimensions: int,
        episode_id: uuid.UUID | None = None,
        memory_fact_id: uuid.UUID | None = None,
    ) -> Embedding:
        """
        Create a new embedding.

        Args:
            org_id: Organization ID
            content: Original text content
            vector: Embedding vector
            model: Model name used for embedding
            dimensions: Vector dimensions
            episode_id: Optional episode ID
            memory_fact_id: Optional memory fact ID

        Returns:
            Created embedding
        """
        embedding = Embedding(
            org_id=org_id,
            content=content,
            vector=vector,
            model=model,
            dimensions=dimensions,
            episode_id=episode_id,
            memory_fact_id=memory_fact_id,
        )
        self.db.add(embedding)
        await self.db.flush()
        return embedding

    async def get_by_id(self, embedding_id: uuid.UUID) -> Embedding | None:
        """Get embedding by ID."""
        result = await self.db.execute(
            select(Embedding).where(Embedding.id == embedding_id)
        )
        return result.scalar_one_or_none()

    async def get_by_episode(
        self, episode_id: uuid.UUID
    ) -> list[Embedding]:
        """Get all embeddings for an episode."""
        result = await self.db.execute(
            select(Embedding).where(Embedding.episode_id == episode_id)
        )
        return list(result.scalars().all())

    async def similarity_search(
        self,
        org_id: uuid.UUID,
        query_vector: list[float],
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[tuple[Embedding, float]]:
        """
        Find similar embeddings using cosine similarity.

        Args:
            org_id: Organization ID for scoping
            query_vector: Query embedding vector
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (embedding, similarity_score) tuples
        """
        # Convert vector to PostgreSQL array format
        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        # Use pgvector's cosine similarity operator
        # 1 - (vector <=> query) gives similarity score (0-1)
        query = text(
            f"""
            SELECT
                id,
                org_id,
                episode_id,
                memory_fact_id,
                content,
                model,
                dimensions,
                vector,
                created_at,
                updated_at,
                1 - (vector <=> '{vector_str}'::vector) as similarity
            FROM embeddings
            WHERE org_id = :org_id
                AND 1 - (vector <=> '{vector_str}'::vector) >= :threshold
            ORDER BY vector <=> '{vector_str}'::vector
            LIMIT :limit
            """
        )

        result = await self.db.execute(
            query,
            {
                "org_id": org_id,
                "threshold": threshold,
                "limit": limit,
            },
        )

        results = []
        for row in result:
            embedding = Embedding(
                id=row.id,
                org_id=row.org_id,
                episode_id=row.episode_id,
                memory_fact_id=row.memory_fact_id,
                content=row.content,
                model=row.model,
                dimensions=row.dimensions,
                vector=row.vector,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            similarity = float(row.similarity)
            results.append((embedding, similarity))

        return results

    async def delete(self, embedding_id: uuid.UUID) -> bool:
        """
        Delete an embedding.

        Args:
            embedding_id: Embedding ID

        Returns:
            True if deleted, False if not found
        """
        embedding = await self.get_by_id(embedding_id)
        if embedding:
            await self.db.delete(embedding)
            await self.db.flush()
            return True
        return False
