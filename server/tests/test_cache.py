"""Tests for cache service."""

from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from app.services.cache import SESSION_TTL, CacheService, make_key


def test_make_key():
    """Test key namespacing helper."""
    key = make_key("session", "user123", "data")
    assert key == "remembr:session:user123:data"

    key = make_key("cache", "test")
    assert key == "remembr:cache:test"


@pytest.mark.asyncio
async def test_cache_set_success():
    """Test successful cache set operation."""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()

    cache = CacheService(redis_mock)

    result = await cache.set("test:key", {"data": "value"}, ttl_seconds=60)

    assert result is True
    redis_mock.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_no_ttl():
    """Test cache set without TTL."""
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock()

    cache = CacheService(redis_mock)

    result = await cache.set("test:key", {"data": "value"})

    assert result is True
    redis_mock.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_error():
    """Test cache set with Redis error."""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock(side_effect=RedisError("Connection failed"))

    cache = CacheService(redis_mock)

    result = await cache.set("test:key", {"data": "value"}, ttl_seconds=60)

    assert result is False


@pytest.mark.asyncio
async def test_cache_get_hit():
    """Test successful cache get (hit)."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value='{"data": "value"}')

    cache = CacheService(redis_mock)

    result = await cache.get("test:key")

    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_cache_get_miss():
    """Test cache get with miss."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)

    cache = CacheService(redis_mock)

    result = await cache.get("test:key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_get_error():
    """Test cache get with Redis error."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(side_effect=RedisError("Connection failed"))

    cache = CacheService(redis_mock)

    result = await cache.get("test:key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_delete_success():
    """Test successful cache delete."""
    redis_mock = AsyncMock()
    redis_mock.delete = AsyncMock(return_value=1)

    cache = CacheService(redis_mock)

    result = await cache.delete("test:key")

    assert result is True


@pytest.mark.asyncio
async def test_cache_delete_not_found():
    """Test cache delete when key doesn't exist."""
    redis_mock = AsyncMock()
    redis_mock.delete = AsyncMock(return_value=0)

    cache = CacheService(redis_mock)

    result = await cache.delete("test:key")

    assert result is False


@pytest.mark.asyncio
async def test_cache_exists_true():
    """Test cache exists check (key exists)."""
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=1)

    cache = CacheService(redis_mock)

    result = await cache.exists("test:key")

    assert result is True


@pytest.mark.asyncio
async def test_cache_exists_false():
    """Test cache exists check (key doesn't exist)."""
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)

    cache = CacheService(redis_mock)

    result = await cache.exists("test:key")

    assert result is False


@pytest.mark.asyncio
async def test_cache_increment():
    """Test cache increment operation."""
    redis_mock = AsyncMock()
    redis_mock.incrby = AsyncMock(return_value=5)

    cache = CacheService(redis_mock)

    result = await cache.increment("test:counter", amount=2)

    assert result == 5
    redis_mock.incrby.assert_called_once_with("test:counter", 2)


@pytest.mark.asyncio
async def test_cache_ttl():
    """Test TTL check."""
    redis_mock = AsyncMock()
    redis_mock.ttl = AsyncMock(return_value=300)

    cache = CacheService(redis_mock)

    result = await cache.ttl("test:key")

    assert result == 300


@pytest.mark.asyncio
async def test_cache_expire():
    """Test setting expiration."""
    redis_mock = AsyncMock()
    redis_mock.expire = AsyncMock(return_value=True)

    cache = CacheService(redis_mock)

    result = await cache.expire("test:key", SESSION_TTL)

    assert result is True
    redis_mock.expire.assert_called_once_with("test:key", SESSION_TTL)
