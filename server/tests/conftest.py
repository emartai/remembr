"""Pytest configuration and fixtures for tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

pytest_plugins = ("pytest_asyncio",)

_test_engine = None
_TestSessionLocal = None


def _get_test_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazily create test engine/session factory so simple unit tests don't need app settings."""
    global _test_engine, _TestSessionLocal
    if _TestSessionLocal is not None:
        return _TestSessionLocal

    from app.config import get_test_settings

    settings = get_test_settings()
    _test_engine = create_async_engine(
        settings.database_url.get_secret_value().replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
        pool_pre_ping=True,
    )
    _TestSessionLocal = async_sessionmaker(
        _test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _TestSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with isolated schema lifecycle."""
    from app.db.base import Base

    test_session_local = _get_test_session_factory()

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_local() as session:
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database and Redis dependencies overridden."""
    from app.db.redis import close_redis, init_redis
    from app.db.session import get_db
    from app.main import app

    await init_redis()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await close_redis()
