"""Security regression tests for unauthenticated access behavior."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.main import create_app

PUBLIC_ROUTE_PREFIXES = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
}


@pytest.mark.asyncio
async def test_protected_routes_require_auth() -> None:
    app = create_app()

    async def fake_db() -> AsyncGenerator[AsyncSession, None]:
        yield None  # not reached for unauthorized requests

    async def fake_redis() -> AsyncGenerator[Redis, None]:
        yield None  # not reached for unauthorized requests

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_redis] = fake_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        protected_routes: list[tuple[str, str]] = []

        for route in app.routes:
            path = getattr(route, "path", "")
            if not path.startswith("/api/v1"):
                continue

            for method in getattr(route, "methods", set()) or set():
                if method in {"HEAD", "OPTIONS"}:
                    continue
                if (method, path) in PUBLIC_ROUTE_PREFIXES:
                    continue

                test_path = (
                    path.replace("{session_id}", "00000000-0000-0000-0000-000000000000")
                    .replace("{episode_id}", "00000000-0000-0000-0000-000000000000")
                    .replace("{user_id}", "00000000-0000-0000-0000-000000000000")
                    .replace("{key_id}", "00000000-0000-0000-0000-000000000000")
                )
                protected_routes.append((method, test_path))

        for method, path in protected_routes:
            kwargs = {}
            if method in {"POST", "PUT", "PATCH"}:
                kwargs["json"] = {}

            response = await client.request(method, path, **kwargs)
            assert response.status_code in {401, 403}, (
                f"{method} {path} should require auth, got {response.status_code}"
            )
