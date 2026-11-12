"""Abstract base class for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-agnostic interface for text embedding generation."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier string."""

    @property
    @abstractmethod
    def dimensions(self) -> int | None:
        """Output vector dimensions, or None if dynamic."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> tuple[list[float], int]:
        """Return (vector, dimensions) for a single text."""

    async def generate_query_embedding(self, text: str) -> tuple[list[float], int]:
        """Embed a query; symmetric providers retain their existing behavior."""
        return await self.generate_embedding(text)

    @abstractmethod
    async def generate_embeddings_batch(self, texts: list[str]) -> list[tuple[list[float], int]]:
        """Return list of (vector, dimensions) for multiple texts."""


async def embed_query(provider: EmbeddingProvider, text: str) -> tuple[list[float], int]:
    """Keep legacy duck-typed provider overrides working during the transition."""
    method = getattr(provider, "generate_query_embedding", None) or provider.generate_embedding
    return await method(text)
