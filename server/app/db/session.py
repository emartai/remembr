"""Database session management."""

from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url.get_secret_value().replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    echo=settings.log_level == "DEBUG",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Automatically sets the organization context from the request context
    if available, enabling Row-Level Security.
    
    Yields:
        AsyncSession: Database session
    """
    # Import here to avoid circular dependency
    from app.db.rls import set_org_context
    from app.middleware.context import get_current_context
    
    async with AsyncSessionLocal() as session:
        try:
            # Set org context from request context if available
            ctx = get_current_context()
            if ctx and ctx.org_id:
                await set_org_context(session, ctx.org_id)
                logger.debug(
                    "Database session initialized with org context",
                    org_id=str(ctx.org_id),
                )
            
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
