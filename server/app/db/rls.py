"""Row-Level Security (RLS) utilities for multi-tenancy."""

import uuid

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_org_context(session: AsyncSession, org_id: uuid.UUID | str) -> None:
    """
    Set the organization context for the current database session.

    This sets the app.current_org_id configuration parameter which is used
    by Row-Level Security policies to enforce multi-tenancy at the database level.

    IMPORTANT: This must be called at the start of every transaction before
    any queries are executed.

    Args:
        session: Database session
        org_id: Organization UUID

    Example:
        >>> async with AsyncSessionLocal() as session:
        ...     await set_org_context(session, org_id)
        ...     # Now all queries are scoped to this org
        ...     result = await session.execute(select(Episode))
    """
    # Convert to string if UUID
    org_id_str = str(org_id)

    # Set the configuration parameter for this session
    await session.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": org_id_str},
    )

    logger.debug("Organization context set", org_id=org_id_str)


async def get_org_context(session: AsyncSession) -> str | None:
    """
    Get the current organization context.

    Args:
        session: Database session

    Returns:
        Organization ID string or None if not set
    """
    result = await session.execute(
        text("SELECT current_setting('app.current_org_id', true)")
    )
    org_id = result.scalar_one_or_none()
    return org_id


async def clear_org_context(session: AsyncSession) -> None:
    """
    Clear the organization context.

    Args:
        session: Database session
    """
    await session.execute(text("RESET app.current_org_id"))
    logger.debug("Organization context cleared")
