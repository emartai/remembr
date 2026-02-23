"""API key service for agent-to-server authentication."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.api_key import APIKey

# API key prefix for easy identification
API_KEY_PREFIX = "rmbr_"
API_KEY_LENGTH = 32  # Random characters after prefix

# Redis cache TTL for API key lookups (60 seconds)
API_KEY_CACHE_TTL = 60


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    
    Returns:
        Tuple of (raw_key, hashed_key)
        - raw_key: The key to show to the user (only once)
        - hashed_key: SHA256 hash to store in database
    """
    # Generate random key with prefix
    random_part = secrets.token_urlsafe(API_KEY_LENGTH)[:API_KEY_LENGTH]
    raw_key = f"{API_KEY_PREFIX}{random_part}"
    
    # Hash the key for storage
    hashed_key = hash_api_key(raw_key)
    
    return raw_key, hashed_key


def hash_api_key(key: str) -> str:
    """
    Hash an API key using SHA256.
    
    Args:
        key: Raw API key string
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.
    
    Args:
        raw_key: Raw API key from request
        stored_hash: Stored hash from database
        
    Returns:
        True if key matches hash, False otherwise
    """
    computed_hash = hash_api_key(raw_key)
    return secrets.compare_digest(computed_hash, stored_hash)


async def create_api_key(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    user_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    """
    Create a new API key.
    
    Args:
        db: Database session
        org_id: Organization ID
        name: Human-readable name for the key
        user_id: Optional user ID to scope the key
        agent_id: Optional agent ID to scope the key
        expires_at: Optional expiration datetime
        
    Returns:
        Tuple of (APIKey model, raw_key)
        The raw_key should be shown to the user ONCE and never stored
    """
    # Generate key
    raw_key, hashed_key = generate_api_key()
    
    # Create API key record
    api_key = APIKey(
        org_id=org_id,
        user_id=user_id,
        agent_id=agent_id,
        key_hash=hashed_key,
        name=name,
        expires_at=expires_at,
    )
    
    db.add(api_key)
    await db.flush()
    
    logger.info(
        "API key created",
        key_id=str(api_key.id),
        org_id=str(org_id),
        name=name,
        user_id=str(user_id) if user_id else None,
        agent_id=str(agent_id) if agent_id else None,
    )
    
    return api_key, raw_key


async def revoke_api_key(
    db: AsyncSession,
    redis: Redis,
    key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """
    Revoke an API key (soft delete by setting expires_at to now).
    
    Also invalidates the cache entry in Redis.
    
    Args:
        db: Database session
        redis: Redis client
        key_id: API key ID to revoke
        org_id: Organization ID (for authorization check)
        
    Returns:
        True if key was revoked, False if not found
    """
    # Fetch the key to get its hash for cache invalidation
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.org_id == org_id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        return False
    
    # Revoke by setting expires_at to now
    now = datetime.now(timezone.utc)
    await db.execute(
        update(APIKey)
        .where(APIKey.id == key_id, APIKey.org_id == org_id)
        .values(expires_at=now)
    )
    
    # Invalidate cache
    cache_key = f"api_key:{api_key.key_hash}"
    await redis.delete(cache_key)
    
    logger.info(
        "API key revoked",
        key_id=str(key_id),
        org_id=str(org_id),
        name=api_key.name,
    )
    
    return True


async def lookup_api_key(
    db: AsyncSession,
    redis: Redis,
    raw_key: str,
) -> dict | None:
    """
    Look up an API key and return its context.
    
    Uses Redis cache with 60-second TTL to reduce database load.
    
    Args:
        db: Database session
        redis: Redis client
        raw_key: Raw API key from request
        
    Returns:
        Dictionary with {org_id, user_id, agent_id, key_id} or None if invalid
    """
    # Hash the key for lookup
    key_hash = hash_api_key(raw_key)
    cache_key = f"api_key:{key_hash}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.debug("API key cache hit", key_hash=key_hash[:16])
        # Parse cached value: "org_id:user_id:agent_id:key_id"
        parts = cached.split(":")
        return {
            "org_id": uuid.UUID(parts[0]),
            "user_id": uuid.UUID(parts[1]) if parts[1] != "None" else None,
            "agent_id": uuid.UUID(parts[2]) if parts[2] != "None" else None,
            "key_id": uuid.UUID(parts[3]),
        }
    
    # Cache miss - query database
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        logger.warning("API key not found", key_hash=key_hash[:16])
        return None
    
    # Check if expired
    now = datetime.now(timezone.utc)
    if api_key.expires_at and api_key.expires_at <= now:
        logger.warning(
            "API key expired",
            key_id=str(api_key.id),
            expired_at=api_key.expires_at.isoformat(),
        )
        return None
    
    # Update last_used_at (fire and forget, don't wait)
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key.id)
        .values(last_used_at=now)
    )
    
    # Prepare context
    context = {
        "org_id": api_key.org_id,
        "user_id": api_key.user_id,
        "agent_id": api_key.agent_id,
        "key_id": api_key.id,
    }
    
    # Cache the result
    cache_value = f"{api_key.org_id}:{api_key.user_id}:{api_key.agent_id}:{api_key.id}"
    await redis.setex(cache_key, API_KEY_CACHE_TTL, cache_value)
    
    logger.info(
        "API key validated",
        key_id=str(api_key.id),
        org_id=str(api_key.org_id),
    )
    
    return context


async def get_api_key_auth(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    redis: Annotated[Redis, Depends(get_redis)] = None,
) -> dict:
    """
    FastAPI dependency for API key authentication.
    
    Extracts API key from X-API-Key header, validates it,
    and returns context with org_id, user_id, agent_id.
    
    Args:
        x_api_key: API key from X-API-Key header
        db: Database session
        redis: Redis client
        
    Returns:
        Dictionary with {org_id, user_id, agent_id, key_id}
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Validate key format
    if not x_api_key.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Look up key
    context = await lookup_api_key(db, redis, x_api_key)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return context
