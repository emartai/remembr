"""Embedding generation service using Jina AI API."""

import asyncio
from typing import Literal

import httpx
from loguru import logger

from app.config import get_settings


class EmbeddingService:
    """
    Service for generating embeddings using Jina AI API.

    Supports both single and batch embedding generation with automatic
    retry logic for rate limits and transient errors.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.jina_api_key.get_secret_value()
        self.model = self.settings.jina_embedding_model
        self.base_url = "https://api.jina.ai/v1/embeddings"
        self.batch_size = getattr(self.settings, "embedding_batch_size", 100)
        self.max_retries = 3
        self.timeout = 30.0

    async def generate(
        self,
        text: str,
        task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage",
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            task: Task type - "retrieval.passage" for storing,
                  "retrieval.query" for searching

        Returns:
            1024-dimensional embedding vector
        """
        embeddings = await self.generate_batch([text], task=task)
        return embeddings[0]

    async def generate_batch(
        self,
        texts: list[str],
        task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage",
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed (max 2048 per call)
            task: Task type - "retrieval.passage" for storing,
                  "retrieval.query" for searching

        Returns:
            List of 1024-dimensional embedding vectors
        """
        if not texts:
            return []

        if len(texts) > 2048:
            logger.warning(
                f"Batch size {len(texts)} exceeds Jina limit of 2048, "
                "splitting into multiple requests"
            )
            # Split into chunks and process
            all_embeddings = []
            for i in range(0, len(texts), 2048):
                chunk = texts[i : i + 2048]
                chunk_embeddings = await self.generate_batch(chunk, task=task)
                all_embeddings.extend(chunk_embeddings)
            return all_embeddings

        # Make API request with retry logic
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "task": task,
                            "input": texts,
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        embeddings = [item["embedding"] for item in data["data"]]
                        logger.debug(
                            f"Generated {len(embeddings)} embeddings "
                            f"(task={task}, model={self.model})"
                        )
                        return embeddings

                    elif response.status_code == 429:
                        # Rate limit - exponential backoff
                        wait_time = 2**attempt
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    elif response.status_code >= 500:
                        # Server error - retry
                        wait_time = 2**attempt
                        logger.warning(
                            f"Server error {response.status_code}, "
                            f"retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        # Client error - don't retry
                        logger.error(f"Jina API error {response.status_code}: {response.text}")
                        raise ValueError(f"Jina API error {response.status_code}: {response.text}")

            except httpx.TimeoutException:
                wait_time = 2**attempt
                logger.warning(
                    f"Request timeout, retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)
                continue

            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise RuntimeError(f"Failed to generate embeddings after {self.max_retries} attempts")

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(a) != len(b):
            raise ValueError("Vectors must have the same length")

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)
