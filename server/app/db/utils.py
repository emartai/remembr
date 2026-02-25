"""Database utility functions."""

import uuid
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization

T = TypeVar("T")


async def get_or_create_organization(
    db: AsyncSession,
    name: str,
) -> Organization:
    """
    Get or create an organization by name.

    Args:
        db: Database session
        name: Organization name

    Returns:
        Organization instance
    """
    result = await db.execute(select(Organization).where(Organization.name == name))
    org = result.scalar_one_or_none()

    if org is None:
        org = Organization(name=name)
        db.add(org)
        await db.flush()

    return org


async def check_org_access(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """
    Check if a user has access to an organization.

    Args:
        db: Database session
        org_id: Organization ID
        user_id: User ID

    Returns:
        True if user has access, False otherwise
    """
    from app.models import User

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.org_id == org_id,
            User.is_active,
        )
    )
    user = result.scalar_one_or_none()
    return user is not None
