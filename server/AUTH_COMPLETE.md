# Complete Authentication System

## Overview

Remembr API supports two authentication methods:

1. **JWT Authentication** - For user sessions (Prompt 9)
2. **API Key Authentication** - For agents/services (Prompt 10)

## Quick Comparison

| Feature | JWT | API Key |
|---------|-----|---------|
| Use Case | User sessions | Agent auth |
| Header | Authorization: Bearer | X-API-Key |
| Expiration | 30 min | Long/never |
| Refresh | Yes | No |
| Caching | No | Yes (60s) |

## Documentation

- `AUTH.md` - JWT documentation
- `API_KEYS.md` - API key documentation
- `auth_example.py` - Usage examples

## Quick Start

### Register User
```bash
POST /api/v1/auth/register
{"email": "user@example.com", "password": "pass123", "org_name": "Org"}
```

### Create API Key
```bash
POST /api/v1/api-keys
Authorization: Bearer <token>
{"name": "My Key"}
```

### Use JWT
```bash
GET /api/v1/endpoint
Authorization: Bearer <access_token>
```

### Use API Key
```bash
GET /api/v1/endpoint
X-API-Key: rmbr_...
```

## Testing

```bash
pytest server/tests/test_auth.py server/tests/test_api_keys.py -v
```
