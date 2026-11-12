"""Task-specific prefixes and vector-space identities must remain consistent."""

import json
import unittest
from unittest.mock import patch

import httpx

from app.services.embeddings.base import embed_query
from app.services.embeddings.ollama import OllamaEmbeddingProvider


class OllamaTaskEmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def check_requests(self, mode):
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

        client_type = httpx.AsyncClient
        transport = httpx.MockTransport(handler)
        with patch(
            "app.services.embeddings.ollama.httpx.AsyncClient",
            side_effect=lambda **kwargs: client_type(transport=transport, **kwargs),
        ):
            provider = OllamaEmbeddingProvider(model="nomic-embed-text", task_mode=mode)
            await provider.generate_embedding("Document")
            await embed_query(provider, "Question")
            await provider.generate_embeddings_batch(["Second document"])
        return provider, requests

    async def test_default_legacy_behavior_and_model_identity_are_retained(self):
        provider, requests = await self.check_requests("legacy")
        self.assertEqual(provider.model, "nomic-embed-text")
        self.assertEqual(
            [r["prompt"] for r in requests], ["Document", "Question", "Second document"]
        )

    async def test_nomic_mode_uses_distinct_prefixes_and_versioned_identity(self):
        provider, requests = await self.check_requests("nomic_search")
        self.assertEqual(provider.model, "nomic-embed-text|nomic-search-v1")
        self.assertTrue(all(r["model"] == "nomic-embed-text" for r in requests))
        self.assertEqual(
            [r["prompt"] for r in requests],
            [
                "search_document: Document",
                "search_query: Question",
                "search_document: Second document",
            ],
        )

    async def test_legacy_duck_typed_provider_is_still_supported(self):
        class Legacy:
            async def generate_embedding(self, text):
                return [1.0], 1

        self.assertEqual(await embed_query(Legacy(), "Question"), ([1.0], 1))

    def test_unknown_task_modes_are_rejected(self):
        with self.assertRaises(ValueError):
            OllamaEmbeddingProvider(task_mode="unknown")


if __name__ == "__main__":
    unittest.main()
