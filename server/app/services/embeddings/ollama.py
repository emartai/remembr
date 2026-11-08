"""Ollama local embedding provider."""

from __future__ import annotations

import httpx
from loguru import logger

from app.services.embeddings.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by a local Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        task_mode: str = "legacy",
    ) -> None:
        if task_mode not in {"legacy", "nomic_search"}:
            raise ValueError("Ollama task mode must be legacy or nomic_search")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._task_mode = task_mode

    @property
    def model(self) -> str:
        # Version the vector space: prefixed and historical raw vectors must
        # never be compared as if they were the same embedding configuration.
        return self._model if self._task_mode == "legacy" else self._model + "|nomic-search-v1"

    @property
    def dimensions(self) -> int | None:
        return None

    async def generate_embedding(self, text: str) -> tuple[list[float], int]:
        prompt = "search_document: " + text if self._task_mode == "nomic_search" else text
        return await self._embed(prompt)

    async def generate_query_embedding(self, text: str) -> tuple[list[float], int]:
        prompt = "search_query: " + text if self._task_mode == "nomic_search" else text
        return await self._embed(prompt)

    async def _embed(self, prompt: str) -> tuple[list[float], int]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": prompt},
            )
            if response.status_code != 200:
                raise ValueError(f"Ollama error {response.status_code}: {response.text}")
            vector: list[float] = response.json()["embedding"]
            logger.debug(f"Ollama embedding generated, dims={len(vector)}")
            return vector, len(vector)

    async def generate_embeddings_batch(self, texts: list[str]) -> list[tuple[list[float], int]]:
        results = []
        for text in texts:
            results.append(await self.generate_embedding(text))
        return results
