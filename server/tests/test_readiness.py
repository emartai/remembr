from unittest.mock import AsyncMock

import pytest

from app.services import readiness


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [None, "database", "redis", "worker", "embeddings"])
async def test_each_pipeline_dependency_is_required(monkeypatch, failed):
    for component in ("database", "redis", "worker", "embeddings"):
        operation = AsyncMock(
            side_effect=RuntimeError("secret must not leak") if component == failed else None
        )
        monkeypatch.setattr(readiness, f"check_{component}", operation)
    checks = await readiness.get_readiness()
    assert checks == {
        name: "unhealthy" if name == failed else "healthy"
        for name in ("database", "redis", "worker", "embeddings")
    }


@pytest.mark.asyncio
async def test_empty_embedding_is_not_ready(monkeypatch):
    from app.services import embeddings

    provider = AsyncMock()
    provider.generate_embedding.return_value = ([], 0)
    monkeypatch.setattr(embeddings, "get_embedding_provider", lambda: provider)
    with pytest.raises(RuntimeError, match="invalid vector"):
        await readiness.check_embeddings()


def test_endpoint_returns_503_when_pipeline_is_unavailable(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(readiness, "get_readiness", AsyncMock(return_value={"worker": "unhealthy"}))
    response = TestClient(create_app()).get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["data"]["status"] == "not_ready"
