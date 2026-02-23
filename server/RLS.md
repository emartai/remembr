# Row-Level Security (RLS) Guide

## Overview

Remembr uses PostgreSQL Row-Level Security (RLS) as a database-level safety net for multi-tenancy. Even if application code has a bug, the database will prevent cross-organization data access.

## Architecture

```
Application Layer
    ↓
SQLAlchemy Queries (with org_id filter)
    ↓
PostgreSQL RLS Policies (safety net)
    ↓
Data (isolated by org_id)
```

## How RLS Works

### 1. Enable RLS on Tables

```sql
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
```

### 2. Create Policies

Each table has a policy that checks `app.current_org_id`:

```sql
CREATE POLICY sessions_org_isolation ON sessions
USING (org_id = current_setting('app.current_org_id', true)::uuid)
WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid);
```

- **USING**: Controls which rows are visible in SELECT queries
- **WITH CHECK**: Controls which rows can be inserted/updated

### 3. Set Organization Context

Before any query, set the organization context:

```python
from app.db.rls import set_org_context

async with AsyncSessionLocal() as db:
    await set_org_context(db, org_id)
    # Now all queries are scoped to this org
    result = await db.execute(select(Episode))
```

## RLS Functions

### set_org_context()

Sets the organization context for the current session:

```python
from app.db.rls import set_org_context

await set_org_context(session, org_id)
```

This sets the PostgreSQL configuration parameter `app.current_org_id` which is used by RLS policies.

**IMPORTANT**: Must be called at the start of every transaction, before any queries.

### get_org_context()

Gets the current organization context:

```python
from app.db.rls import get_org_context

current_org = await get_org_context(session)
print(f"Current org: {current_org}")
```

### clear_org_context()

Clears the organization context:

```python
from app.db.rls import clear_org_context

await clear_org_context(session)
```

## Usage Patterns

### Basic Query

```python
from app.db.rls import set_org_context
from app.db.session import AsyncSessionLocal
from app.models import Episode

async def get_episodes(org_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        # Set org context first
        await set_org_context(db, org_id)
        
        # Query - RLS automatically filters by org_id
        result = await db.execute(select(Episode))
        episodes = result.scalars().all()
        
        return episodes
```

### Insert with RLS

```python
async def create_episode(org_id: uuid.UUID, content: str):
    async with AsyncSessionLocal() as db:
        # Set org context
        await set_org_context(db, org_id)
        
        # Create episode
        episode = Episode(
            org_id=org_id,
            role="user",
            content=content,
        )
        db.add(episode)
        await db.commit()
        
        return episode
```

### Update with RLS

```python
async def update_episode(org_id: uuid.UUID, episode_id: uuid.UUID, content: str):
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_id)
        
        # Get episode (RLS ensures it belongs to org)
        result = await db.execute(
            select(Episode).where(Episode.id == episode_id)
        )
        episode = result.scalar_one_or_none()
        
        if episode:
            episode.content = content
            await db.commit()
        
        return episode
```

### Delete with RLS

```python
async def delete_episode(org_id: uuid.UUID, episode_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_id)
        
        # Get episode (RLS ensures it belongs to org)
        result = await db.execute(
            select(Episode).where(Episode.id == episode_id)
        )
        episode = result.scalar_one_or_none()
        
        if episode:
            await db.delete(episode)
            await db.commit()
            return True
        
        return False
```

## Security Benefits

### 1. Defense in Depth

RLS provides a second layer of security:

```python
# Even if you forget to filter by org_id in application code...
result = await db.execute(select(Episode))  # Missing WHERE clause!

# ...RLS still prevents cross-org access
episodes = result.scalars().all()  # Only returns current org's episodes
```

### 2. Protection Against SQL Injection

Even with SQL injection, RLS prevents data leakage:

```python
# Malicious input trying to access other orgs
malicious_input = "' OR org_id != org_id --"

# Even if this gets into a query, RLS blocks it
result = await db.execute(
    text(f"SELECT * FROM episodes WHERE content = '{malicious_input}'")
)
# RLS ensures only current org's data is returned
```

### 3. Protection Against Application Bugs

If application code has a bug that forgets org_id filtering:

```python
# Bug: Missing org_id filter
async def get_all_episodes():  # WRONG!
    result = await db.execute(select(Episode))
    return result.scalars().all()

# RLS still protects - only returns current org's episodes
```

## Performance Considerations

### Index Usage

RLS policies use the `org_id` index, so performance is good:

```sql
-- This query uses the org_id index
SELECT * FROM episodes WHERE org_id = current_setting('app.current_org_id')::uuid;
```

### Query Plans

Check that RLS doesn't hurt performance:

```sql
-- Set org context
SET app.current_org_id = 'uuid-here';

-- Explain query
EXPLAIN ANALYZE SELECT * FROM episodes;
```

Should show index scan on `org_id`.

### Overhead

RLS adds minimal overhead:
- ~1-2% query time increase
- Worth it for the security benefits

## Testing RLS

### Test Cross-Org Isolation

```python
@pytest.mark.asyncio
async def test_rls_isolation():
    # Create data for org A
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a_id)
        episode_a = Episode(org_id=org_a_id, content="Org A data")
        db.add(episode_a)
        await db.commit()
    
    # Query as org B - should not see org A's data
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_b_id)
        result = await db.execute(select(Episode))
        episodes = result.scalars().all()
        
        # Should be empty
        assert len(episodes) == 0
```

### Test Insert Protection

```python
@pytest.mark.asyncio
async def test_rls_insert_protection():
    async with AsyncSessionLocal() as db:
        # Set context to org A
        await set_org_context(db, org_a_id)
        
        # Try to insert for org B (should fail)
        episode = Episode(org_id=org_b_id, content="Wrong org")
        db.add(episode)
        
        # RLS WITH CHECK clause prevents this
        with pytest.raises(Exception):
            await db.commit()
```

## Troubleshooting

### No Results Returned

If queries return empty results:

1. Check org context is set:
```python
current_org = await get_org_context(db)
print(f"Current org: {current_org}")
```

2. Verify org_id matches:
```python
# Check if data exists for this org
result = await db.execute(
    text("SELECT COUNT(*) FROM episodes WHERE org_id = :org_id"),
    {"org_id": org_id}
)
count = result.scalar()
print(f"Episodes for org: {count}")
```

### Permission Denied Errors

If you get permission errors:

1. Check RLS is enabled:
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```

2. Check policies exist:
```sql
SELECT * FROM pg_policies WHERE tablename = 'episodes';
```

### Performance Issues

If queries are slow:

1. Check indexes exist:
```sql
SELECT * FROM pg_indexes WHERE tablename = 'episodes';
```

2. Analyze query plan:
```sql
EXPLAIN ANALYZE SELECT * FROM episodes;
```

3. Ensure org_id index is used:
```sql
-- Should show "Index Scan using ix_episodes_org_id"
```

## Best Practices

### 1. Always Set Context First

```python
# Good
async with AsyncSessionLocal() as db:
    await set_org_context(db, org_id)
    result = await db.execute(select(Episode))

# Bad - context not set
async with AsyncSessionLocal() as db:
    result = await db.execute(select(Episode))  # Returns nothing!
```

### 2. Set Context Once Per Transaction

```python
# Good - set once at start
async with AsyncSessionLocal() as db:
    await set_org_context(db, org_id)
    
    # Multiple queries use same context
    episodes = await db.execute(select(Episode))
    sessions = await db.execute(select(Session))

# Bad - setting multiple times (unnecessary)
async with AsyncSessionLocal() as db:
    await set_org_context(db, org_id)
    episodes = await db.execute(select(Episode))
    
    await set_org_context(db, org_id)  # Redundant!
    sessions = await db.execute(select(Session))
```

### 3. Still Filter by org_id in Application

RLS is a safety net, not a replacement for application-level filtering:

```python
# Good - explicit org_id filter + RLS
result = await db.execute(
    select(Episode).where(Episode.org_id == org_id)
)

# Acceptable - RLS provides safety net
result = await db.execute(select(Episode))
```

### 4. Test RLS Policies

Always test that RLS prevents cross-org access:

```python
# Test that org A cannot see org B's data
async def test_cross_org_isolation():
    # Create data for both orgs
    # Query as org A
    # Verify only org A's data is visible
```

### 5. Monitor RLS Performance

Track query performance with RLS enabled:

```python
import time

start = time.time()
result = await db.execute(select(Episode))
duration = time.time() - start

logger.info("Query duration", duration=duration)
```

## Migration Guide

### Enabling RLS

Run the migration:

```bash
alembic upgrade head
```

This enables RLS on:
- sessions
- episodes
- memory_facts
- embeddings

### Disabling RLS (Not Recommended)

If you need to disable RLS temporarily:

```sql
ALTER TABLE episodes DISABLE ROW LEVEL SECURITY;
```

To re-enable:

```sql
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
```

## Advanced Topics

### Bypassing RLS

Database superusers bypass RLS by default. To test RLS as superuser:

```sql
-- Disable bypass
ALTER ROLE postgres NORLS;

-- Re-enable bypass
ALTER ROLE postgres RLS;
```

### Multiple Policies

You can have multiple policies per table:

```sql
-- Policy for regular users
CREATE POLICY user_access ON episodes
USING (org_id = current_setting('app.current_org_id')::uuid);

-- Policy for admins (can see all)
CREATE POLICY admin_access ON episodes
USING (current_setting('app.user_role') = 'admin');
```

### Policy Debugging

Check which policies apply:

```sql
SELECT * FROM pg_policies WHERE tablename = 'episodes';
```

View policy definitions:

```sql
\d+ episodes
```

## Resources

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [RLS Performance Tips](https://www.postgresql.org/docs/current/sql-createpolicy.html)
