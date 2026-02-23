# Redis Integration Guide

## Overview

Remembr uses Redis (via Upstash) for:
- Session state management
- Short-term memory caching
- Rate limiting
- Temporary data storage

## Architecture

```
FastAPI Application
    ↓
Redis Client (async)
    ↓
Connection Pool (20 connections)
    ↓
Upstash Redis (TLS)
    ↓
Cached Data (JSON serialized)
```

## Configuration

### Environment Variables

```bash
# Redis connection string (from Upstash)
REDIS_URL=rediss://default:password@endpoint.upstash.io:6379
```

### Connection Pool

- **Max connections**: 20
- **Encoding**: UTF-8
- **Decode responses**: True (automatic string decoding)
- **TLS**: Enabled (rediss://)

## Redis Client

### Initialization

Redis is initialized during application startup:

```python
from app.db.redis import init_redis, close_redis

# Startup
await init_redis()

# Shutdown
await close_redis()
```

### Dependency Injection

Use the `get_redis()` dependency in FastAPI routes:

```python
from fastapi import Depends
from redis.asyncio import Redis
from app.db.redis import get_redis

@router.get("/example")
async def example(redis: Redis = Depends(get_redis)):
    await redis.set("key", "value")
    value = await redis.get("key")
    return {"value": value}
```

### Direct Access

For use outside FastAPI routes:

```python
from app.db.redis import get_redis_client

redis = get_redis_client()
await redis.ping()
```

## Cache Service

### Overview

The `CacheService` provides a high-level interface for Redis operations with:
- Automatic JSON serialization/deserialization
- Key namespacing
- TTL management
- Error handling

### Basic Usage

```python
from app.db.redis import get_redis
from app.services import CacheService

redis = get_redis()
cache = CacheService(redis)

# Set value with TTL
await cache.set("user:123", {"name": "John"}, ttl_seconds=3600)

# Get value
user = await cache.get("user:123")  # Returns dict or None

# Delete value
await cache.delete("user:123")

# Check existence
exists = await cache.exists("user:123")  # Returns bool
```

### Key Namespacing

Always use `make_key()` for consistent key naming:

```python
from app.services.cache import make_key

# Create namespaced keys
session_key = make_key("session", user_id, "data")
# Result: "remembr:session:user123:data"

agent_key = make_key("agent", agent_id, "state")
# Result: "remembr:agent:agent456:state"

cache_key = make_key("cache", "embeddings", episode_id)
# Result: "remembr:cache:embeddings:episode789"
```

### TTL Constants

Pre-defined TTL values:

```python
from app.services.cache import (
    SESSION_TTL,      # 3600 seconds (1 hour)
    SHORT_TERM_TTL,   # 1800 seconds (30 minutes)
    LONG_TERM_TTL,    # 86400 seconds (24 hours)
)

# Use in cache operations
await cache.set(key, value, ttl_seconds=SESSION_TTL)
```

## Common Patterns

### Session Management

```python
from app.services.cache import make_key, SESSION_TTL

# Store session data
session_key = make_key("session", session_id)
await cache.set(
    session_key,
    {
        "user_id": user_id,
        "agent_id": agent_id,
        "created_at": datetime.utcnow().isoformat(),
    },
    ttl_seconds=SESSION_TTL,
)

# Retrieve session
session_data = await cache.get(session_key)
if session_data:
    user_id = session_data["user_id"]

# Extend session TTL
await cache.expire(session_key, SESSION_TTL)

# Delete session
await cache.delete(session_key)
```

### Caching Database Queries

```python
from app.services.cache import make_key, SHORT_TERM_TTL

async def get_user_with_cache(user_id: str):
    # Try cache first
    cache_key = make_key("user", user_id)
    cached = await cache.get(cache_key)
    
    if cached:
        return cached
    
    # Cache miss - query database
    user = await db.get(User, user_id)
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
    }
    
    # Store in cache
    await cache.set(cache_key, user_dict, ttl_seconds=SHORT_TERM_TTL)
    
    return user_dict
```

### Rate Limiting

```python
from app.services.cache import make_key

async def check_rate_limit(user_id: str, limit: int = 100) -> bool:
    """Check if user is within rate limit."""
    key = make_key("ratelimit", user_id, "requests")
    
    # Increment counter
    count = await cache.increment(key)
    
    if count == 1:
        # First request - set TTL to 1 hour
        await cache.expire(key, 3600)
    
    return count <= limit
```

### Temporary Data Storage

```python
from app.services.cache import make_key, SHORT_TERM_TTL

# Store temporary processing results
async def store_processing_result(task_id: str, result: dict):
    key = make_key("task", task_id, "result")
    await cache.set(key, result, ttl_seconds=SHORT_TERM_TTL)

# Retrieve and delete
async def get_and_clear_result(task_id: str):
    key = make_key("task", task_id, "result")
    result = await cache.get(key)
    if result:
        await cache.delete(key)
    return result
```

### Batch Operations

```python
# Set multiple values
data = {
    make_key("user", "123", "name"): "Alice",
    make_key("user", "456", "name"): "Bob",
    make_key("user", "789", "name"): "Charlie",
}
await cache.set_many(data, ttl_seconds=3600)

# Get multiple values
keys = [
    make_key("user", "123", "name"),
    make_key("user", "456", "name"),
]
results = await cache.get_many(keys)
```

### Pattern Deletion

```python
# Delete all session keys for a user
pattern = make_key("session", user_id, "*")
deleted = await cache.delete_pattern(pattern)
print(f"Deleted {deleted} keys")

# Delete all cache entries
pattern = make_key("cache", "*")
await cache.delete_pattern(pattern)
```

## Error Handling

### Graceful Degradation

The cache service handles errors gracefully:

```python
# If Redis is down, operations return safe defaults
result = await cache.get("key")  # Returns None on error
success = await cache.set("key", "value")  # Returns False on error
exists = await cache.exists("key")  # Returns False on error
```

### Connection Errors

```python
from redis.exceptions import RedisError

try:
    await cache.set("key", "value")
except RedisError as e:
    logger.error("Redis operation failed", error=str(e))
    # Continue without cache
```

### Application Startup

If Redis fails to connect during startup:
- Application continues to run
- Warning is logged
- Cache operations will fail gracefully

## Health Check

The `/api/v1/health` endpoint includes Redis status:

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "ok",
  "environment": "local",
  "version": "0.1.0",
  "redis_status": "healthy"
}
```

Redis status values:
- `healthy`: Connected and responding
- `unhealthy`: Connection error
- `not_initialized`: Redis not initialized
- `error`: Unexpected error

## Monitoring

### Key Metrics

Monitor these Redis metrics:

1. **Connection count**: Should stay below max_connections (20)
2. **Memory usage**: Track cache size
3. **Hit rate**: Cache hits / total requests
4. **Latency**: Response time for operations

### Upstash Dashboard

View metrics in Upstash console:
- Commands per second
- Memory usage
- Connection count
- Latency percentiles

### Application Logging

Cache operations are logged with loguru:

```python
# Debug logs for cache operations
logger.debug("Cache hit", key=key)
logger.debug("Cache miss", key=key)
logger.debug("Cache set", key=key, ttl=ttl_seconds)

# Error logs for failures
logger.error("Cache operation failed", key=key, error=str(e))
```

## Best Practices

### 1. Always Use Namespacing

```python
# Good
key = make_key("session", user_id)

# Bad
key = f"session:{user_id}"  # Inconsistent format
```

### 2. Set Appropriate TTLs

```python
# Short-lived data (30 min)
await cache.set(key, value, ttl_seconds=SHORT_TERM_TTL)

# Session data (1 hour)
await cache.set(key, value, ttl_seconds=SESSION_TTL)

# Long-lived data (24 hours)
await cache.set(key, value, ttl_seconds=LONG_TERM_TTL)

# Permanent data (no TTL)
await cache.set(key, value)  # Use sparingly
```

### 3. Handle Cache Misses

```python
# Always check for None
cached = await cache.get(key)
if cached is None:
    # Fetch from database
    data = await fetch_from_db()
    await cache.set(key, data, ttl_seconds=SHORT_TERM_TTL)
else:
    data = cached
```

### 4. Invalidate on Updates

```python
async def update_user(user_id: str, data: dict):
    # Update database
    await db.update(User, user_id, data)
    
    # Invalidate cache
    cache_key = make_key("user", user_id)
    await cache.delete(cache_key)
```

### 5. Use Batch Operations

```python
# Good: Single round trip
await cache.set_many(data_dict)

# Bad: Multiple round trips
for key, value in data_dict.items():
    await cache.set(key, value)
```

### 6. Serialize Complex Objects

```python
from datetime import datetime
from uuid import UUID

# Convert to JSON-serializable types
data = {
    "id": str(user.id),  # UUID -> str
    "created_at": user.created_at.isoformat(),  # datetime -> str
    "metadata": user.metadata,  # dict is fine
}
await cache.set(key, data)
```

## Troubleshooting

### Connection Refused

If Redis connection fails:

1. Check `REDIS_URL` is correct
2. Verify Upstash database is active
3. Check network connectivity
4. Verify TLS is enabled (`rediss://`)

### Slow Operations

If cache operations are slow:

1. Check Upstash region (should be close to app)
2. Monitor connection pool usage
3. Reduce batch sizes
4. Check network latency

### Memory Issues

If Redis memory is full:

1. Review TTL settings (too long?)
2. Check for memory leaks (keys without TTL)
3. Implement cache eviction policy
4. Upgrade Upstash plan

### Serialization Errors

If JSON serialization fails:

```python
# Check for non-serializable types
import json

try:
    json.dumps(data)
except TypeError as e:
    print(f"Cannot serialize: {e}")
    # Convert problematic types
```

## Testing

### Unit Tests

```python
import pytest
from app.services.cache import CacheService, make_key

@pytest.mark.asyncio
async def test_cache_set_get(redis_client):
    cache = CacheService(redis_client)
    
    key = make_key("test", "key")
    value = {"data": "test"}
    
    # Set value
    success = await cache.set(key, value, ttl_seconds=60)
    assert success
    
    # Get value
    result = await cache.get(key)
    assert result == value
    
    # Clean up
    await cache.delete(key)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_session_management(cache_service):
    session_id = "test-session-123"
    session_key = make_key("session", session_id)
    
    # Create session
    session_data = {"user_id": "user-456"}
    await cache_service.set(
        session_key,
        session_data,
        ttl_seconds=SESSION_TTL,
    )
    
    # Retrieve session
    retrieved = await cache_service.get(session_key)
    assert retrieved["user_id"] == "user-456"
    
    # Check TTL
    ttl = await cache_service.ttl(session_key)
    assert 0 < ttl <= SESSION_TTL
```

## Resources

- [Redis Documentation](https://redis.io/docs/)
- [Upstash Documentation](https://docs.upstash.com/redis)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [FastAPI with Redis](https://fastapi.tiangolo.com/advanced/async-sql-databases/)
