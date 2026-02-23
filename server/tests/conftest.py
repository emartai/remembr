"""Pytest configuration and fixtures for tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_test_settings
from app.db.base import Base
from app.db.redis import close_redis, init_redis
from app.db.session import get_db
from app.main import app

# Get test settings
settings = get_test_settings()

# Create test engine
test_engine = create_async_engine(
    settings.database_url.get_secret_value().replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    echo=False,
    pool_pre_ping=True,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.
    
    Creates all tables before the test and drops them after.
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client with database and Redis dependencies overridden.
    """
    # Initialize Redis
    await init_redis()
    
    # Override database dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()
    await close_redis()
