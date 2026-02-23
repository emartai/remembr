"""Embedding generation service using Jina AI."""

import httpx
from loguru import logger

from app.config import get_settings


class EmbeddingService:
    """Service for generating embeddings using Jina AI API."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.jina_api_key.get_secret_value()
        self.model = self.settings.jina_embedding_model
        self.base_url = "https://api.jina.ai/v1/embeddings"

    async def generate_embedding(self, text: str) -> tuple[list[float], int]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Tuple of (embedding vector, dimensions)

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": [text],
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            dimensions = len(embedding)

            logger.debug(
                "Generated embedding",
                model=self.model,
                dimensions=dimensions,
                text_length=len(text),
            )

            return embedding, dimensions

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[tuple[list[float], int]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            List of tuples (embedding vector, dimensions)

        Raises:
            httpx.HTTPError: If API request fails
        """
        if not texts:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()

            data = response.json()
            results = []
            for item in data["data"]:
                embedding = item["embedding"]
                dimensions = len(embedding)
                results.append((embedding, dimensions))

            logger.debug(
                "Generated batch embeddings",
                model=self.model,
                count=len(texts),
                dimensions=dimensions if results else 0,
            )

            return results
