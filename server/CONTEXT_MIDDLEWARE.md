# Request Context Middleware

Multi-tenant request context middleware that extracts authentication details from JWT or API key and injects them into a request-scoped context using Python contextvars.

## Overview

The context middleware provides:

1. **Unified Authentication**: Tries JWT first, falls back to API key
2. **Request-Scoped Context**: Uses contextvars for async-safe context storage
3. **Automatic RLS**: Database sessions automatically set org context
4. **Context-Aware Logging**: All logs include org_id, user_id, request_id
5. **Flexible Dependencies**: Optional or required authentication

## Architecture

```
Request → Middleware → get_request_context()
                           ↓
                    Try JWT Auth
                           ↓
                    Try API Key Auth
                           ↓
                    Store in contextvars
                           ↓
                    get_db() sets RLS
                           ↓
                    Endpoint Handler
```

## Components

### RequestContext Dataclass

```python
@dataclass
class RequestContext:
    request_id: str
    org_id: uuid.UUID
    user_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    auth_method: str  # "jwt" or "api_key"
```

### Dependencies

#### `get_request_context()` - Optional Auth

Returns `RequestContext | None`. Use when authentication is optional.

```python
from app.middleware.context import get_request_context, RequestContext

@router.get("/optional")
async def optional_endpoint(
    ctx: RequestContext | None = Depends(get_request_context),
):
    if ctx:
        return {"authenticated": True, "org_id": str(ctx.org_id)}
    return {"authenticated": False}
```

#### `require_auth()` - Required Auth

Returns `RequestContext` or raises 401. Use when authentication is required.

```python
from app.middleware.context import require_auth, RequestContext

@router.get("/protected")
async def protected_endpoint(
    ctx: RequestContext = Depends(require_auth),
):
    return {
        "org_id": str(ctx.org_id),
        "user_id": str(ctx.user_id),
        "auth_method": ctx.auth_method,
    }
```

#### `get_current_context()` - Access Anywhere

Access context from anywhere in the call stack without passing it.

```python
from app.middleware.context import get_current_context

def helper_function():
    ctx = get_current_context()
    if ctx:
        logger.info("Processing", org_id=str(ctx.org_id))
```

## Authentication Flow

### JWT Authentication

1. Extract `Authorization: Bearer <token>` header
2. Decode JWT and validate signature
3. Verify token type is "access"
4. Fetch user from database
5. Check user is active
6. Extract agent_id from token if present
7. Return RequestContext

### API Key Authentication

1. Extract `X-API-Key` header
2. Hash the key and look up in database
3. Check Redis cache first (60s TTL)
4. Verify key is not expired
5. Update last_used_at timestamp
6. Return RequestContext

### Fallback Behavior

- JWT is tried first
- If JWT fails, API key is tried
- If both fail, returns None
- `require_auth()` raises 401 if None

## Database Integration

The `get_db()` dependency automatically sets the organization context for Row-Level Security:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        # Automatically set org context from request context
        ctx = get_current_context()
        if ctx and ctx.org_id:
            await set_org_context(session, ctx.org_id)
        
        yield session
```

This ensures all database queries are automatically scoped to the authenticated organization.

## Logging Integration

The middleware in `main.py` automatically adds context to all log messages:

```python
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = str(uuid.uuid4())
    
    log_context = {"request_id": request_id}
    
    # After authentication
    ctx = get_current_context()
    if ctx:
        log_context.update({
            "org_id": str(ctx.org_id),
            "user_id": str(ctx.user_id) if ctx.user_id else None,
            "agent_id": str(ctx.agent_id) if ctx.agent_id else None,
            "auth_method": ctx.auth_method,
        })
    
    with logger.contextualize(**log_context):
        # All logs in this request include context
        logger.info("Request completed")
```

Every log line automatically includes:
- `request_id`: Unique request identifier
- `org_id`: Organization ID (if authenticated)
- `user_id`: User ID (if authenticated)
- `agent_id`: Agent ID (if present)
- `auth_method`: "jwt" or "api_key" (if authenticated)

## Usage Examples

### Protected Endpoint

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.context import RequestContext, require_auth

router = APIRouter()

@router.get("/memories")
async def list_memories(
    ctx: Annotated[RequestContext, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # ctx contains org_id, user_id, agent_id
    # db session already has org context set for RLS
    
    result = await db.execute(select(Memory))
    memories = result.scalars().all()
    
    return {"memories": memories}
```

### Optional Authentication

```python
@router.get("/public")
async def public_endpoint(
    ctx: Annotated[RequestContext | None, Depends(get_request_context)],
):
    if ctx:
        return {"message": "Authenticated", "org_id": str(ctx.org_id)}
    return {"message": "Anonymous"}
```

### Service Functions

```python
from app.middleware.context import get_current_context

async def process_data(db: AsyncSession):
    # Access context without passing it
    ctx = get_current_context()
    
    if not ctx:
        raise ValueError("No authentication context")
    
    logger.info("Processing data", org_id=str(ctx.org_id))
    
    # Database queries are automatically scoped to ctx.org_id
    result = await db.execute(select(Data))
    return result.scalars().all()
```

## Testing

The test suite covers:

- JWT authentication success/failure
- API key authentication success/failure
- Inactive users
- Expired keys
- Authentication fallback
- Context storage in contextvars
- Protected endpoints
- Optional authentication

Run tests:

```bash
pytest server/tests/test_context.py -v
```

## Security Considerations

1. **Async Safety**: Uses contextvars instead of thread-locals
2. **Token Validation**: JWT signature and expiry checked
3. **User Status**: Inactive users rejected
4. **Key Expiry**: Expired API keys rejected
5. **RLS Enforcement**: org_id set on every DB transaction
6. **Cache Security**: Redis cache has 60s TTL
7. **Constant-Time Comparison**: API key hashes compared with secrets.compare_digest

## Performance

- **JWT**: ~1ms (decode + DB lookup)
- **API Key (cached)**: ~0.1ms (Redis lookup)
- **API Key (uncached)**: ~2ms (DB lookup + cache set)
- **Context Storage**: ~0.01ms (contextvars)

## Migration Guide

### Before (Manual Auth)

```python
@router.get("/endpoint")
async def endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_org_context(db, current_user.org_id)
    # ...
```

### After (Automatic Context)

```python
@router.get("/endpoint")
async def endpoint(
    ctx: RequestContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # org context already set automatically
    # ...
```

## Troubleshooting

### Context is None

- Check authentication headers are present
- Verify JWT is valid and not expired
- Verify API key exists and not expired
- Check user is active

### RLS Not Working

- Ensure `get_db()` is used as dependency
- Verify context is set before DB queries
- Check RLS policies are enabled

### Logs Missing Context

- Verify middleware is registered in main.py
- Check context is set before logging
- Ensure using loguru with contextualize

## References

- [JWT Authentication](./AUTH.md)
- [API Key Authentication](./API_KEYS.md)
- [Row-Level Security](./RLS.md)
- [Database Session Management](./DATABASE.md)
