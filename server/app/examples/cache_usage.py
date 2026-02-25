"""
Example usage of Redis cache service.

This file demonstrates common caching patterns in Remembr.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.db.redis import get_redis
from app.services.cache import (
    SESSION_TTL,
    SHORT_TERM_TTL,
    CacheService,
    make_key,
)

router = APIRouter()


# Example 1: Session Management
@router.post("/sessions/{session_id}")
async def create_session(
    session_id: str,
    user_id: str,
    redis: Redis = Depends(get_redis),
):
    """Create a new session in cache."""
    cache = CacheService(redis)

    session_key = make_key("session", session_id)
    session_data = {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
    }

    await cache.set(session_key, session_data, ttl_seconds=SESSION_TTL)

    return {"session_id": session_id, "ttl": SESSION_TTL}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    redis: Redis = Depends(get_redis),
):
    """Retrieve session from cache."""
    cache = CacheService(redis)

    session_key = make_key("session", session_id)
    session_data = await cache.get(session_key)

    if not session_data:
        return {"error": "Session not found or expired"}

    # Extend session TTL on access
    await cache.expire(session_key, SESSION_TTL)

    return session_data


# Example 2: Query Result Caching
@router.get("/users/{user_id}")
async def get_user_cached(
    user_id: str,
    redis: Redis = Depends(get_redis),
):
    """Get user with caching."""
    cache = CacheService(redis)

    # Try cache first
    cache_key = make_key("user", user_id)
    cached_user = await cache.get(cache_key)

    if cached_user:
        return {"user": cached_user, "source": "cache"}

    # Simulate database query
    user_data = {
        "id": user_id,
        "email": f"user{user_id}@example.com",
        "name": f"User {user_id}",
    }

    # Store in cache
    await cache.set(cache_key, user_data, ttl_seconds=SHORT_TERM_TTL)

    return {"user": user_data, "source": "database"}


# Example 3: Rate Limiting
@router.post("/api/action")
async def rate_limited_action(
    user_id: str,
    redis: Redis = Depends(get_redis),
):
    """Example of rate limiting with Redis."""
    cache = CacheService(redis)

    # Check rate limit (100 requests per hour)
    rate_key = make_key("ratelimit", user_id, "requests")

    # Increment counter
    count = await cache.increment(rate_key)

    if count == 1:
        # First request - set TTL to 1 hour
        await cache.expire(rate_key, 3600)

    if count > 100:
        return {"error": "Rate limit exceeded", "retry_after": 3600}

    # Get remaining TTL
    ttl = await cache.ttl(rate_key)

    return {
        "success": True,
        "requests_remaining": 100 - count,
        "reset_in": ttl,
    }


# Example 4: Temporary Processing Results
@router.post("/tasks/{task_id}/result")
async def store_task_result(
    task_id: str,
    result: dict,
    redis: Redis = Depends(get_redis),
):
    """Store temporary task result."""
    cache = CacheService(redis)

    result_key = make_key("task", task_id, "result")
    await cache.set(result_key, result, ttl_seconds=SHORT_TERM_TTL)

    return {"task_id": task_id, "stored": True}


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    redis: Redis = Depends(get_redis),
):
    """Retrieve and optionally clear task result."""
    cache = CacheService(redis)

    result_key = make_key("task", task_id, "result")
    result = await cache.get(result_key)

    if not result:
        return {"error": "Task result not found or expired"}

    # Optionally delete after retrieval
    await cache.delete(result_key)

    return {"result": result}


# Example 5: Batch Operations
@router.post("/cache/batch")
async def batch_cache_operations(
    redis: Redis = Depends(get_redis),
):
    """Example of batch cache operations."""
    cache = CacheService(redis)

    # Set multiple values at once
    data = {
        make_key("temp", "key1"): {"value": 1},
        make_key("temp", "key2"): {"value": 2},
        make_key("temp", "key3"): {"value": 3},
    }

    await cache.set_many(data, ttl_seconds=300)

    # Get multiple values at once
    keys = list(data.keys())
    results = await cache.get_many(keys)

    return {"stored": len(data), "retrieved": len(results)}


# Example 6: Cache Invalidation
@router.delete("/users/{user_id}/cache")
async def invalidate_user_cache(
    user_id: str,
    redis: Redis = Depends(get_redis),
):
    """Invalidate all cache entries for a user."""
    cache = CacheService(redis)

    # Delete all user-related cache keys
    pattern = make_key("user", user_id, "*")
    deleted = await cache.delete_pattern(pattern)

    return {"deleted_keys": deleted}
