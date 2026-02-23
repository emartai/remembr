# Database Schema Documentation

## Overview

Remembr uses PostgreSQL with the following features:
- Multi-tenancy with organization-level isolation
- UUID primary keys
- Timezone-aware timestamps (TIMESTAMPTZ)
- JSONB for flexible metadata
- Array types for tags
- Async SQLAlchemy for high performance

## Multi-Tenancy Architecture

Every table includes `org_id` to ensure data isolation between organizations:

```
┌─────────────────┐
│  organizations  │ (Root)
└────────┬────────┘
         │
         ├─── teams
         ├─── users
         ├─── agents
         ├─── api_keys
         ├─── sessions
         ├─── episodes
         └─── memory_facts
```

## Table Schemas

### organizations

Root table for multi-tenancy.

| Column     | Type         | Constraints | Description           |
|------------|--------------|-------------|-----------------------|
| id         | UUID         | PK          | Organization ID       |
| name       | VARCHAR(255) | NOT NULL    | Organization name     |
| created_at | TIMESTAMPTZ  | NOT NULL    | Creation timestamp    |
| updated_at | TIMESTAMPTZ  | NOT NULL    | Last update timestamp |

### teams

Groups users within an organization.

| Column     | Type         | Constraints      | Description        |
|------------|--------------|------------------|--------------------|
| id         | UUID         | PK               | Team ID            |
| org_id     | UUID         | FK, NOT NULL, IX | Organization ID    |
| name       | VARCHAR(255) | NOT NULL         | Team name          |
| created_at | TIMESTAMPTZ  | NOT NULL         | Creation timestamp |

### users

User accounts for authentication.

| Column          | Type         | Constraints           | Description        |
|-----------------|--------------|---------------------- |--------------------|
| id              | UUID         | PK                    | User ID            |
| org_id          | UUID         | FK, NOT NULL, IX      | Organization ID    |
| team_id         | UUID         | FK, NULL, IX          | Team ID (optional) |
| email           | VARCHAR(255) | UNIQUE, NOT NULL, IX  | Email address      |
| hashed_password | VARCHAR(255) | NOT NULL              | Password hash      |
| is_active       | BOOLEAN      | NOT NULL              | Account status     |
| created_at      | TIMESTAMPTZ  | NOT NULL              | Creation timestamp |

### agents

AI agents using the memory system.

| Column      | Type         | Constraints      | Description        |
|-------------|--------------|------------------|--------------------|
| id          | UUID         | PK               | Agent ID           |
| org_id      | UUID         | FK, NOT NULL, IX | Organization ID    |
| team_id     | UUID         | FK, NULL, IX     | Team ID (optional) |
| user_id     | UUID         | FK, NULL, IX     | Owner user ID      |
| name        | VARCHAR(255) | NOT NULL         | Agent name         |
| description | TEXT         | NULL             | Agent description  |
| created_at  | TIMESTAMPTZ  | NOT NULL         | Creation timestamp |

### api_keys

Authentication keys for API access.

| Column       | Type         | Constraints           | Description        |
|--------------|--------------|---------------------- |--------------------|
| id           | UUID         | PK                    | API key ID         |
| org_id       | UUID         | FK, NOT NULL, IX      | Organization ID    |
| user_id      | UUID         | FK, NULL, IX          | User ID (optional) |
| agent_id     | UUID         | FK, NULL, IX          | Agent ID (optional)|
| key_hash     | VARCHAR(255) | UNIQUE, NOT NULL, IX  | Hashed key         |
| name         | VARCHAR(255) | NOT NULL              | Key name           |
| last_used_at | TIMESTAMPTZ  | NULL                  | Last usage time    |
| expires_at   | TIMESTAMPTZ  | NULL                  | Expiration time    |
| created_at   | TIMESTAMPTZ  | NOT NULL              | Creation timestamp |

### sessions

Conversation or interaction contexts.

| Column     | Type        | Constraints      | Description        |
|------------|-------------|------------------|--------------------|
| id         | UUID        | PK               | Session ID         |
| org_id     | UUID        | FK, NOT NULL, IX | Organization ID    |
| team_id    | UUID        | FK, NULL, IX     | Team ID (optional) |
| user_id    | UUID        | FK, NULL, IX     | User ID (optional) |
| agent_id   | UUID        | FK, NULL, IX     | Agent ID (optional)|
| metadata   | JSONB       | NULL             | Custom metadata    |
| created_at | TIMESTAMPTZ | NOT NULL, IX     | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL         | Last update time   |
| expires_at | TIMESTAMPTZ | NULL             | Expiration time    |

### episodes

Individual messages or interactions.

| Column     | Type         | Constraints      | Description        |
|------------|--------------|------------------|--------------------|
| id         | UUID         | PK               | Episode ID         |
| org_id     | UUID         | FK, NOT NULL, IX | Organization ID    |
| team_id    | UUID         | FK, NULL, IX     | Team ID (optional) |
| user_id    | UUID         | FK, NULL, IX     | User ID (optional) |
| agent_id   | UUID         | FK, NULL, IX     | Agent ID (optional)|
| session_id | UUID         | FK, NULL, IX     | Session ID         |
| role       | VARCHAR(50)  | NOT NULL         | Message role       |
| content    | TEXT         | NOT NULL         | Message content    |
| tags       | TEXT[]       | NULL, GIN IX     | Tags array         |
| metadata   | JSONB        | NULL             | Custom metadata    |
| created_at | TIMESTAMPTZ  | NOT NULL, IX     | Creation timestamp |

### memory_facts

Extracted knowledge as subject-predicate-object triples.

| Column            | Type        | Constraints      | Description           |
|-------------------|-------------|------------------|-----------------------|
| id                | UUID        | PK               | Fact ID               |
| org_id            | UUID        | FK, NOT NULL, IX | Organization ID       |
| team_id           | UUID        | FK, NULL, IX     | Team ID (optional)    |
| user_id           | UUID        | FK, NULL, IX     | User ID (optional)    |
| agent_id          | UUID        | FK, NULL, IX     | Agent ID (optional)   |
| source_episode_id | UUID        | FK, NULL, IX     | Source episode ID     |
| subject           | TEXT        | NOT NULL         | Triple subject        |
| predicate         | TEXT        | NOT NULL         | Triple predicate      |
| object            | TEXT        | NOT NULL         | Triple object         |
| confidence        | FLOAT       | NOT NULL, DEF 1.0| Confidence score      |
| valid_from        | TIMESTAMPTZ | NOT NULL         | Validity start        |
| valid_until       | TIMESTAMPTZ | NULL             | Validity end          |
| created_at        | TIMESTAMPTZ | NOT NULL         | Creation timestamp    |
| updated_at        | TIMESTAMPTZ | NOT NULL         | Last update timestamp |

## Indexes

### Standard Indexes

All tables have indexes on:
- Primary keys (UUID)
- Foreign keys (org_id, team_id, user_id, agent_id, etc.)

### Special Indexes

- `episodes.created_at` - B-tree index for time-based queries
- `episodes.tags` - GIN index for array containment queries
- `sessions.created_at` - B-tree index for time-based queries
- `users.email` - Unique index for authentication
- `api_keys.key_hash` - Unique index for authentication

## Relationships

### Cascade Behavior

- **CASCADE**: When parent is deleted, children are deleted
  - Organization → All child tables
  - Session → Episodes

- **SET NULL**: When parent is deleted, foreign key is set to NULL
  - Team → Users, Agents, etc.
  - User → Agents, Episodes, etc.
  - Agent → Episodes, Memory Facts, etc.

## Data Types

### UUID
- All primary keys use UUID v4
- Generated server-side with `gen_random_uuid()`
- Provides global uniqueness

### TIMESTAMPTZ
- All timestamps include timezone information
- Stored in UTC
- Automatically converted to local timezone on retrieval

### JSONB
- Binary JSON format for efficient storage and querying
- Used for flexible metadata fields
- Supports indexing and querying

### ARRAY
- Native PostgreSQL array type
- Used for tags on episodes
- GIN indexed for fast containment queries

## Query Patterns

### Organization Scoping

Always filter by org_id:

```python
from sqlalchemy import select
from app.models import Episode

# Get episodes for an organization
result = await db.execute(
    select(Episode)
    .where(Episode.org_id == org_id)
    .order_by(Episode.created_at.desc())
)
episodes = result.scalars().all()
```

### Tag Queries

Use array operators:

```python
# Episodes with specific tag
result = await db.execute(
    select(Episode)
    .where(Episode.tags.contains(['important']))
)

# Episodes with any of multiple tags
result = await db.execute(
    select(Episode)
    .where(Episode.tags.overlap(['urgent', 'important']))
)
```

### JSONB Queries

Query nested JSON:

```python
# Query metadata field
result = await db.execute(
    select(Session)
    .where(Session.metadata['key'].astext == 'value')
)
```

### Temporal Queries

Query valid facts:

```python
from datetime import datetime

now = datetime.utcnow()
result = await db.execute(
    select(MemoryFact)
    .where(
        MemoryFact.valid_from <= now,
        (MemoryFact.valid_until == None) | (MemoryFact.valid_until > now)
    )
)
```

## Performance Considerations

### Connection Pooling

- Pool size: 5 connections
- Max overflow: 10 connections
- Pre-ping enabled for connection health checks

### Query Optimization

1. Always use indexes for filtering
2. Limit result sets with `.limit()`
3. Use `.options()` for eager loading relationships
4. Avoid N+1 queries with `selectinload()` or `joinedload()`

### Async Best Practices

```python
# Good: Use async session
async with AsyncSessionLocal() as session:
    result = await session.execute(query)
    
# Bad: Blocking operations
result = session.execute(query)  # Missing await
```

## Security

### SQL Injection Prevention

- Always use parameterized queries
- Never concatenate user input into SQL
- SQLAlchemy handles escaping automatically

### Data Isolation

- Every query must filter by org_id
- Implement middleware to enforce organization scoping
- Validate user access before queries

### Password Storage

- Never store plain text passwords
- Use bcrypt or argon2 for hashing
- Store only hashed_password in database

## Backup and Recovery

### Backup

```bash
# Full backup
pg_dump $DATABASE_URL > backup.sql

# Schema only
pg_dump --schema-only $DATABASE_URL > schema.sql

# Data only
pg_dump --data-only $DATABASE_URL > data.sql
```

### Restore

```bash
# Restore full backup
psql $DATABASE_URL < backup.sql

# Restore to new database
createdb remembr_restore
psql remembr_restore < backup.sql
```

## Monitoring

### Useful Queries

```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```
