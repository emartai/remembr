# Query Performance Guide

## Overview

This guide covers query optimization, index usage, and performance monitoring for Remembr.

## Index Strategy

### Primary Indexes

All tables have these indexes:

1. **Primary Key (UUID)**: Clustered index on `id`
2. **Organization ID**: B-tree index on `org_id` (critical for RLS)
3. **Foreign Keys**: Indexes on all FK columns
4. **Timestamps**: Indexes on `created_at` for time-based queries

### Special Indexes

1. **GIN Index on Tags**: For array containment queries
   ```sql
   CREATE INDEX ix_episodes_tags ON episodes USING gin (tags);
   ```

2. **HNSW Index on Vectors**: For similarity search
   ```sql
   CREATE INDEX ix_embeddings_vector_cosine ON embeddings 
   USING hnsw (vector vector_cosine_ops);
   ```

## Query Patterns

### 1. Organization-Scoped Queries

Always filter by `org_id` first:

```python
# Good - uses org_id index
result = await db.execute(
    select(Episode)
    .where(Episode.org_id == org_id)
    .order_by(Episode.created_at.desc())
)

# Bad - full table scan
result = await db.execute(
    select(Episode).order_by(Episode.created_at.desc())
)
```

### 2. Time-Based Queries

Use `created_at` index for time ranges:

```python
from datetime import datetime, timedelta

# Get recent episodes
since = datetime.utcnow() - timedelta(days=7)
result = await db.execute(
    select(Episode)
    .where(
        Episode.org_id == org_id,
        Episode.created_at >= since,
    )
    .order_by(Episode.created_at.desc())
)
```

### 3. Tag Queries

Use GIN index for tag searches:

```python
# Contains tag
result = await db.execute(
    select(Episode)
    .where(
        Episode.org_id == org_id,
        Episode.tags.contains(['important']),
    )
)

# Overlaps with tags
result = await db.execute(
    select(Episode)
    .where(
        Episode.org_id == org_id,
        Episode.tags.overlap(['urgent', 'important']),
    )
)
```

### 4. Vector Similarity Search

Use HNSW index for fast similarity search:

```python
from sqlalchemy import text

# Cosine similarity search
query = text("""
    SELECT *, 1 - (vector <=> :query_vector::vector) as similarity
    FROM embeddings
    WHERE org_id = :org_id
        AND 1 - (vector <=> :query_vector::vector) >= :threshold
    ORDER BY vector <=> :query_vector::vector
    LIMIT :limit
""")

result = await db.execute(
    query,
    {
        "org_id": org_id,
        "query_vector": vector_str,
        "threshold": 0.7,
        "limit": 10,
    }
)
```

## Query Optimization

### Use EXPLAIN ANALYZE

Check query plans:

```python
from sqlalchemy import text

# Analyze query
result = await db.execute(
    text("EXPLAIN ANALYZE SELECT * FROM episodes WHERE org_id = :org_id"),
    {"org_id": org_id}
)

for row in result:
    print(row[0])
```

Expected output:
```
Index Scan using ix_episodes_org_id on episodes
  Index Cond: (org_id = 'uuid-here')
  Planning Time: 0.123 ms
  Execution Time: 1.234 ms
```

### Avoid N+1 Queries

Use eager loading:

```python
from sqlalchemy.orm import selectinload

# Good - single query with join
result = await db.execute(
    select(Episode)
    .options(selectinload(Episode.session))
    .where(Episode.org_id == org_id)
)

# Bad - N+1 queries
episodes = await db.execute(select(Episode).where(Episode.org_id == org_id))
for episode in episodes.scalars():
    session = await db.get(Session, episode.session_id)  # Extra query!
```

### Limit Result Sets

Always use `.limit()` for large result sets:

```python
# Good - limited results
result = await db.execute(
    select(Episode)
    .where(Episode.org_id == org_id)
    .order_by(Episode.created_at.desc())
    .limit(100)
)

# Bad - could return millions of rows
result = await db.execute(
    select(Episode).where(Episode.org_id == org_id)
)
```

### Use Pagination

Implement cursor-based pagination:

```python
async def get_episodes_paginated(
    org_id: uuid.UUID,
    cursor: datetime | None = None,
    limit: int = 50,
):
    query = select(Episode).where(Episode.org_id == org_id)
    
    if cursor:
        query = query.where(Episode.created_at < cursor)
    
    query = query.order_by(Episode.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    episodes = result.scalars().all()
    
    next_cursor = episodes[-1].created_at if episodes else None
    
    return episodes, next_cursor
```

## Index Monitoring

### Check Index Usage

```sql
-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Find Unused Indexes

```sql
-- Indexes with zero scans
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public';
```

### Index Size

```sql
-- Index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Connection Pooling

### Configuration

Current pool settings:

```python
engine = create_async_engine(
    database_url,
    pool_size=5,        # Normal connections
    max_overflow=10,    # Extra connections under load
    pool_pre_ping=True, # Check connection health
)
```

### Monitoring

Check pool status:

```python
from app.db.session import engine

# Pool statistics
print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
print(f"Overflow: {engine.pool.overflow()}")
```

### Tuning

Adjust based on load:

```python
# High traffic
pool_size=20
max_overflow=30

# Low traffic
pool_size=5
max_overflow=10
```

## Caching Strategy

### Query Result Caching

Cache expensive queries:

```python
from app.services.cache import make_key, SHORT_TERM_TTL

async def get_user_stats(user_id: uuid.UUID):
    # Try cache first
    cache_key = make_key("stats", "user", str(user_id))
    cached = await cache.get(cache_key)
    
    if cached:
        return cached
    
    # Expensive query
    result = await db.execute(
        text("""
            SELECT
                COUNT(*) as episode_count,
                COUNT(DISTINCT session_id) as session_count
            FROM episodes
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    stats = result.fetchone()._asdict()
    
    # Cache for 30 minutes
    await cache.set(cache_key, stats, ttl_seconds=SHORT_TERM_TTL)
    
    return stats
```

### Invalidation Strategy

Invalidate cache on updates:

```python
async def create_episode(user_id: uuid.UUID, content: str):
    # Create episode
    episode = Episode(user_id=user_id, content=content)
    db.add(episode)
    await db.commit()
    
    # Invalidate user stats cache
    cache_key = make_key("stats", "user", str(user_id))
    await cache.delete(cache_key)
    
    return episode
```

## Slow Query Logging

### Enable in PostgreSQL

```sql
-- Log queries slower than 100ms
ALTER DATABASE remembr SET log_min_duration_statement = 100;

-- View slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Application Logging

Log slow queries in application:

```python
import time
from loguru import logger

async def execute_with_timing(query):
    start = time.time()
    result = await db.execute(query)
    duration = time.time() - start
    
    if duration > 0.1:  # 100ms threshold
        logger.warning(
            "Slow query detected",
            duration=duration,
            query=str(query),
        )
    
    return result
```

## Performance Benchmarks

### Expected Query Times

| Query Type | Expected Time | Notes |
|------------|---------------|-------|
| Single row by ID | <5ms | Uses PK index |
| Org-scoped list (100 rows) | <20ms | Uses org_id index |
| Tag search | <50ms | Uses GIN index |
| Vector similarity (10 results) | <100ms | Uses HNSW index |
| Aggregation query | <200ms | Depends on data size |

### Load Testing

Use locust or similar:

```python
from locust import HttpUser, task, between

class RemembrUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_episodes(self):
        self.client.get("/api/v1/episodes")
    
    @task
    def create_episode(self):
        self.client.post("/api/v1/episodes", json={
            "content": "Test episode",
            "role": "user",
        })
```

## Troubleshooting

### Slow Queries

1. Check indexes exist:
```sql
\d+ episodes
```

2. Analyze query plan:
```sql
EXPLAIN ANALYZE SELECT * FROM episodes WHERE org_id = 'uuid';
```

3. Look for:
   - Sequential scans (bad)
   - Index scans (good)
   - High execution time

### High Memory Usage

1. Check connection pool:
```python
print(engine.pool.checkedout())
```

2. Reduce pool size if needed

3. Check for connection leaks:
```python
# Always use context managers
async with AsyncSessionLocal() as db:
    # Query here
    pass  # Connection automatically closed
```

### Lock Contention

Check for locks:

```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

Avoid long transactions:

```python
# Bad - long transaction
async with AsyncSessionLocal() as db:
    # Many operations...
    await db.commit()

# Good - short transactions
async with AsyncSessionLocal() as db:
    # Single operation
    await db.commit()
```

## Best Practices

1. **Always filter by org_id first**
2. **Use indexes for WHERE clauses**
3. **Limit result sets**
4. **Use pagination for large datasets**
5. **Cache expensive queries**
6. **Monitor slow queries**
7. **Use connection pooling**
8. **Avoid N+1 queries**
9. **Use EXPLAIN ANALYZE**
10. **Keep transactions short**

## Resources

- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [pgvector Performance](https://github.com/pgvector/pgvector#performance)
