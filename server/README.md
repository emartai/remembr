# Remembr Server

FastAPI-based memory service for AI agents.

## Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and configure the required variables:

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string with pgvector extension
- `REDIS_URL`: Redis connection string (Upstash recommended)
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `JINA_API_KEY`: Get from https://jina.ai/

### Optional Variables

- `SENTRY_DSN`: For error tracking (leave empty if not using)
- `ENVIRONMENT`: Set to `local`, `staging`, or `production`
- `LOG_LEVEL`: Set to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`

## Running the Server

### Development Mode

```bash
cd server

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

The server will start at http://localhost:8000

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

When running in local or staging environments:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "ok",
  "environment": "local",
  "version": "0.1.0"
}
```

## Features

### Request ID Tracking

Every request gets a unique UUID that is:
- Attached to all log entries
- Returned in the `X-Request-ID` response header
- Included in error responses

### Structured Logging

All logs are output in JSON format with:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `request_id`: Unique request identifier
- `message`: Log message
- Additional context fields

### Error Handling

All errors follow a consistent format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "request_id": "uuid-here"
  }
}
```

### Sentry Integration

If `SENTRY_DSN` is configured, all errors are automatically reported to Sentry with:
- Full stack traces
- Request context
- Environment information

## Configuration

All configuration is managed through Pydantic Settings in `app/config.py`:

```python
from app.config import get_settings

settings = get_settings()
db_url = settings.database_url.get_secret_value()
redis_url = settings.redis_url.get_secret_value()
```

For testing, use `get_test_settings()` which automatically uses a separate test database.

## Redis

### Cache Service

Redis is used for session management and caching:

```python
from app.db.redis import get_redis
from app.services import CacheService

redis = get_redis()
cache = CacheService(redis)

# Set value with TTL
await cache.set("key", {"data": "value"}, ttl_seconds=3600)

# Get value
value = await cache.get("key")
```

See [REDIS.md](./REDIS.md) for complete Redis integration guide.

## Database

### Schema

The database uses a multi-tenant architecture with organization-level isolation. See [DATABASE.md](./DATABASE.md) for complete schema documentation.

### Migrations

Database migrations are managed with Alembic:

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history
```

See [MIGRATIONS.md](./MIGRATIONS.md) for detailed migration guide.

### Initialize Sample Data

```bash
python scripts/init_db.py
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/test_main.py
```
