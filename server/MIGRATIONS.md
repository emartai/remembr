# Database Migrations Guide

This guide covers database schema management using Alembic.

## Prerequisites

- PostgreSQL 14+ with asyncpg driver installed
- Environment variables configured (DATABASE_URL)
- Server dependencies installed

## Quick Start

### Run Migrations

```bash
cd server

# Upgrade to latest version
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade 001
```

### Check Current Version

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

## Creating New Migrations

### Auto-generate Migration

After modifying models in `app/models/`:

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated migration file in alembic/versions/
# Edit if necessary

# Apply the migration
alembic upgrade head
```

### Create Empty Migration

For data migrations or custom SQL:

```bash
alembic revision -m "description"
```

## Migration File Structure

Migrations are stored in `server/alembic/versions/` with this naming format:
```
YYYYMMDD_HHMM_REV_description.py
```

Example:
```
20260223_1800_001_initial_schema.py
```

## Database Schema

### Multi-Tenancy Model

All tables include `org_id` for organization-level isolation:

```
organizations (root)
├── teams
├── users
├── agents
├── api_keys
├── sessions
├── episodes
└── memory_facts
```

### Tables

#### organizations
- Root table for multi-tenancy
- All data scoped to an organization

#### teams
- Groups users within an organization
- Optional team-level scoping

#### users
- User accounts for authentication
- Belongs to organization and optionally a team

#### agents
- AI agents using the memory system
- Can be owned by users or teams

#### api_keys
- Authentication keys for API access
- Can be scoped to users or agents

#### sessions
- Conversation or interaction contexts
- Groups related episodes

#### episodes
- Individual messages or interactions
- Atomic units of memory
- Supports tags (GIN indexed) and metadata (JSONB)

#### memory_facts
- Extracted knowledge as subject-predicate-object triples
- Temporal validity (valid_from, valid_until)
- Confidence scores
- Links to source episodes

### Indexes

All tables have indexes on:
- Primary keys (UUID)
- Foreign keys (org_id, team_id, user_id, agent_id, etc.)
- created_at on episodes and sessions
- tags on episodes (GIN index for array search)

## Common Operations

### Upgrade to Latest

```bash
alembic upgrade head
```

### Downgrade to Base

```bash
alembic downgrade base
```

### Upgrade/Downgrade to Specific Version

```bash
# Upgrade to version 002
alembic upgrade 002

# Downgrade to version 001
alembic downgrade 001
```

### Show SQL Without Executing

```bash
# Show upgrade SQL
alembic upgrade head --sql

# Show downgrade SQL
alembic downgrade -1 --sql
```

### Stamp Database

Mark database as being at a specific version without running migrations:

```bash
alembic stamp head
```

## Environment Configuration

Alembic reads database URL from `app/config.py`:

```python
from app.config import get_settings

settings = get_settings()
database_url = settings.database_url.get_secret_value()
```

The URL is automatically converted from `postgresql://` to `postgresql+asyncpg://` for async support.

## Testing Migrations

### Test Upgrade

```bash
# Downgrade to base
alembic downgrade base

# Upgrade to head
alembic upgrade head

# Verify schema
psql $DATABASE_URL -c "\dt"
```

### Test Downgrade

```bash
# Downgrade one version
alembic downgrade -1

# Verify schema
psql $DATABASE_URL -c "\dt"

# Upgrade back
alembic upgrade head
```

## Production Deployment

### Railway

Migrations run automatically on deployment if configured in `railway.toml`:

```toml
[deploy]
startCommand = "alembic upgrade head && uvicorn server.app.main:app --host 0.0.0.0 --port $PORT"
```

Or run manually using Railway CLI:

```bash
railway run alembic upgrade head
```

### Manual Deployment

1. Backup database:
```bash
pg_dump $DATABASE_URL > backup.sql
```

2. Run migrations:
```bash
alembic upgrade head
```

3. Verify:
```bash
alembic current
```

4. If issues occur, rollback:
```bash
alembic downgrade -1
```

## Troubleshooting

### "Can't locate revision identified by 'XXX'"

The database is at a version not in your migrations folder.

Solution:
```bash
# Check current version
alembic current

# Stamp to a known version
alembic stamp head
```

### "Target database is not up to date"

Your code expects a newer schema than the database has.

Solution:
```bash
alembic upgrade head
```

### "Multiple heads detected"

You have branching migration history.

Solution:
```bash
# View heads
alembic heads

# Merge heads
alembic merge heads -m "merge branches"
```

### Connection Errors

Verify DATABASE_URL is correct:

```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"

# Check environment variable
echo $DATABASE_URL
```

### Import Errors

Ensure all models are imported in `alembic/env.py`:

```python
from app.models import (
    Agent,
    APIKey,
    Episode,
    MemoryFact,
    Organization,
    Session,
    Team,
    User,
)
```

## Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations** on a copy of production data
3. **Backup database** before running migrations in production
4. **Use descriptive migration messages**
5. **Keep migrations small and focused**
6. **Never edit applied migrations** - create a new one instead
7. **Include both upgrade and downgrade** paths
8. **Test downgrade** to ensure it works

## Migration Checklist

Before applying a migration:

- [ ] Reviewed generated SQL
- [ ] Tested upgrade on development database
- [ ] Tested downgrade on development database
- [ ] Backed up production database
- [ ] Verified no data loss
- [ ] Checked for breaking changes
- [ ] Updated documentation
- [ ] Notified team of schema changes

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
