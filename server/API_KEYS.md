# API Key Authentication System

API key authentication for agent-to-server communication where OAuth flows are not practical.

## Overview

The API key system provides a simple, secure way for agents and services to authenticate with the Remembr API without requiring interactive login flows. API keys are scoped to organizations and can optionally be associated with specific users or agents.

## Features

- **Secure Generation**: Keys use cryptographically secure random generation
- **SHA256 Hashing**: Only hashed keys stored in database
- **One-Time Display**: Raw keys shown only once at creation
- **Redis Caching**: 60-second cache TTL to reduce database load
- **Cache Invalidation**: Automatic cache clearing on revocation
- **Organization Scoping**: Keys cannot be used across organizations
- **Expiration Support**: Optional expiration dates
- **Usage Tracking**: Last used timestamp updated on each use
- **Soft Deletion**: Revocation sets expiration to now

## Architecture

### Components

1. **Service Layer** (`app/services/api_keys.py`)
   - Key generation and hashing
   - Key creation and revocation
   - Key lookup with caching
   - Authentication dependency

2. **API Layer** (`app/api/v1/api_keys.py`)
   - Create API key endpoint (JWT auth required)
   - List API keys endpoint (JWT auth required)
   - Revoke API key endpoint (JWT auth required)

3. **Storage**
   - PostgreSQL: API key metadata and hashes
   - Redis: Cached key lookups (60s TTL)

## API Key Format

```
rmbr_<32_random_characters>
```

Example: `rmbr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

## API Endpoints

### POST /api/v1/api-keys

Create a new API key (requires JWT authentication).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "name": "Production Agent Key",
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**Response (201):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Production Agent Key",
  "api_key": "rmbr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "org_id": "123e4567-e89b-12d3-a456-426614174001",
  "user_id": "123e4567-e89b-12d3-a456-426614174002",
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**⚠️ IMPORTANT**: The `api_key` field contains the raw key and is shown ONLY ONCE. Store it securely - it cannot be retrieved later.

### GET /api/v1/api-keys

List all API keys for the current user's organization.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "keys": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Production Agent Key",
      "org_id": "123e4567-e89b-12d3-a456-426614174001",
      "user_id": "123e4567-e89b-12d3-a456-426614174002",
      "agent_id": "123e4567-e89b-12d3-a456-426614174003",
      "last_used_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-12-31T23:59:59Z",
      "created_at": "2024-01-01T00:00:00Z",
      "is_expired": false
    }
  ],
  "total": 1
}
```

**Note**: Raw API keys are NEVER returned in list responses.

### DELETE /api/v1/api-keys/{key_id}

Revoke an API key.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (204):** No content

## Using API Keys

### In HTTP Requests

Include the API key in the `X-API-Key` header:

```bash
curl -X GET https://api.remembr.ai/api/v1/some-endpoint \
  -H "X-API-Key: rmbr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

### In Python

```python
import httpx

api_key = "rmbr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.remembr.ai/api/v1/some-endpoint",
        headers={"X-API-Key": api_key}
    )
```

### In JavaScript/TypeScript

```typescript
const apiKey = "rmbr_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6";

const response = await fetch("https://api.remembr.ai/api/v1/some-endpoint", {
  headers: {
    "X-API-Key": apiKey
  }
});
```

## Protecting Routes with API Keys

Use the `get_api_key_auth` dependency to protect routes:

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from app.services.api_keys import get_api_key_auth

router = APIRouter()

@router.get("/agent-endpoint")
async def agent_endpoint(
    auth: Annotated[dict, Depends(get_api_key_auth)],
):
    # auth contains: {org_id, user_id, agent_id, key_id}
    org_id = auth["org_id"]
    agent_id = auth["agent_id"]
    
    return {"message": f"Authenticated as org {org_id}"}
```

## Supporting Both JWT and API Key Auth

You can create endpoints that accept either authentication method:

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from app.models.user import User
from app.services.auth import get_current_user
from app.services.api_keys import get_api_key_auth

router = APIRouter()

async def get_auth_context(
    jwt_user: Annotated[User | None, Depends(get_current_user)] = None,
    api_key_auth: Annotated[dict | None, Depends(get_api_key_auth)] = None,
):
    """Accept either JWT or API key authentication."""
    if jwt_user:
        return {"org_id": jwt_user.org_id, "user_id": jwt_user.id}
    elif api_key_auth:
        return api_key_auth
    else:
        raise HTTPException(status_code=401, detail="Authentication required")

@router.get("/flexible-endpoint")
async def flexible_endpoint(
    auth: Annotated[dict, Depends(get_auth_context)],
):
    return {"org_id": str(auth["org_id"])}
```

## Security Features

### Key Generation

- Uses `secrets.token_urlsafe()` for cryptographically secure random generation
- 32 characters of randomness (192 bits of entropy)
- Prefixed with `rmbr_` for easy identification

### Key Storage

- Only SHA256 hash stored in database
- Raw keys never logged or persisted
- Constant-time comparison prevents timing attacks

### Key Validation

- Format validation (must start with `rmbr_`)
- Expiration checking
- Organization scoping (keys cannot cross org boundaries)
- Usage tracking (last_used_at updated on each use)

### Caching

- Redis cache with 60-second TTL
- Reduces database load for frequently used keys
- Automatic invalidation on revocation
- Cache key format: `api_key:<sha256_hash>`

### Revocation

- Soft delete (sets expires_at to now)
- Immediate cache invalidation
- Keys remain in database for audit trail

## Best Practices

1. **Store Keys Securely**
   - Use environment variables or secret management systems
   - Never commit keys to version control
   - Rotate keys periodically

2. **Use Descriptive Names**
   - Name keys by their purpose: "Production Agent", "CI/CD Pipeline"
   - Makes management and auditing easier

3. **Set Expiration Dates**
   - Use short-lived keys for temporary access
   - Set expiration for keys with known end dates

4. **Scope Keys Appropriately**
   - Associate keys with specific agents when possible
   - Helps with access control and auditing

5. **Monitor Usage**
   - Check `last_used_at` to identify unused keys
   - Revoke keys that haven't been used recently

6. **Revoke Compromised Keys**
   - Immediately revoke if a key is exposed
   - Create a new key to replace it

7. **Use HTTPS**
   - Always use HTTPS to protect keys in transit
   - Never send keys over unencrypted connections

## Error Responses

| Status | Error | Cause |
|--------|-------|-------|
| 401 | Missing API key | No X-API-Key header provided |
| 401 | Invalid API key format | Key doesn't start with `rmbr_` |
| 401 | Invalid or expired API key | Key not found or expired |
| 404 | API key not found | Key doesn't exist or wrong org |

## Caching Behavior

### Cache Hit Flow
1. Request arrives with API key
2. Hash the key
3. Check Redis cache
4. Return cached context (org_id, user_id, agent_id)

### Cache Miss Flow
1. Request arrives with API key
2. Hash the key
3. Cache miss - query database
4. Validate expiration
5. Update last_used_at
6. Store in cache with 60s TTL
7. Return context

### Cache Invalidation
1. Key revoked via API
2. Set expires_at to now in database
3. Delete cache entry
4. Subsequent requests will fail validation

## Performance Considerations

- **Cache Hit**: ~1ms (Redis lookup only)
- **Cache Miss**: ~10-50ms (database query + cache write)
- **Cache TTL**: 60 seconds (balances freshness vs. load)
- **Revocation**: Immediate (cache invalidated synchronously)

## Monitoring and Auditing

### Key Metrics to Track

- Total active keys per organization
- Key usage frequency (via last_used_at)
- Cache hit rate
- Failed authentication attempts
- Key creation/revocation events

### Logging

All key operations are logged with structured data:

```python
# Key creation
logger.info("API key created", key_id=..., org_id=..., name=...)

# Key validation
logger.info("API key validated", key_id=..., org_id=...)

# Key revocation
logger.info("API key revoked", key_id=..., org_id=..., name=...)

# Failed validation
logger.warning("API key not found", key_hash=...)
logger.warning("API key expired", key_id=..., expired_at=...)
```

## Migration from Other Auth Methods

If migrating from another authentication system:

1. Create API keys for existing agents
2. Update agent code to use X-API-Key header
3. Test in staging environment
4. Deploy to production
5. Monitor for authentication errors
6. Deprecate old authentication method

## Testing

### Unit Tests

```bash
pytest server/tests/test_api_keys.py -v
```

### Integration Testing

```bash
# Create a key
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key"}'

# Use the key
curl -X GET http://localhost:8000/api/v1/some-endpoint \
  -H "X-API-Key: <api_key>"

# List keys
curl -X GET http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <jwt_token>"

# Revoke key
curl -X DELETE http://localhost:8000/api/v1/api-keys/<key_id> \
  -H "Authorization: Bearer <jwt_token>"
```

## Troubleshooting

### Key Not Working

1. Check key format (must start with `rmbr_`)
2. Verify key hasn't expired
3. Confirm key belongs to correct organization
4. Check if key was revoked
5. Verify X-API-Key header is set correctly

### Cache Issues

1. Check Redis connection
2. Verify cache TTL settings
3. Monitor cache hit/miss rates
4. Check for cache invalidation on revoke

### Performance Issues

1. Monitor cache hit rate (should be >90%)
2. Check database query performance
3. Verify Redis latency
4. Consider increasing cache TTL if appropriate

## Future Enhancements

Potential improvements:

- Rate limiting per API key
- IP whitelisting for keys
- Key rotation automation
- Webhook notifications on key events
- Key usage analytics dashboard
- Scoped permissions per key
- Multiple keys per agent
- Key templates for common use cases
