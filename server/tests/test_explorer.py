"""The public explorer shell serves only local assets; API authorization is separate."""

import httpx
import pytest

from app.main import app


@pytest.fixture(autouse=True)
def isolated_asset_checks(monkeypatch):
    # Asset checks do not need a live Redis rate-limit backend.
    from app.middleware.rate_limit import limiter

    monkeypatch.setattr(limiter, "enabled", False)


@pytest.mark.asyncio
async def test_explorer_shell_and_same_origin_assets():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/explorer")
        assert response.status_code == 200
        assert "Memory explorer" in response.text
        assert "default-src 'none'" in response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["cache-control"] == "no-store"
        for asset, media_type in (("explorer.js", "javascript"), ("explorer.css", "text/css")):
            result = await client.get("/explorer/" + asset)
            assert result.status_code == 200
            assert media_type in result.headers["content-type"]
            assert result.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_explorer_does_not_expose_arbitrary_files():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/explorer/router.py")
        assert response.status_code == 404
