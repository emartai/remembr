# Authentication System

JWT-based authentication with access tokens and refresh tokens for the Remembr API.

## Overview

The authentication system provides secure user registration, login, token refresh, and logout functionality using JWT (JSON Web Tokens) with bcrypt password hashing.

## Features

- **Password Security**: Bcrypt hashing with automatic salt generation
- **JWT Tokens**: Separate access and refresh tokens with different expiration times
- **Token Invalidation**: Refresh tokens can be invalidated on logout using Redis
- **User Management**: Registration creates both user and organization
- **Protected Endpoints**: FastAPI dependency for route protection

## Architecture

### Components

1. **Service Layer** (`app/services/auth.py`)
   - Password hashing and verification
   - JWT token creation and decoding
   - User authentication dependency

2. **API Layer** (`app/api/v1/auth.py`)
   - Registration endpoint
   - Login endpoint
   - Token refresh endpoint
   - Logout endpoint
   - Current user endpoint

3. **Storage**
   - PostgreSQL: User credentials and profile data
   - Redis: Invalidated refresh tokens (with TTL)

## API Endpoints

### POST /api/v1/auth/register

Register a new user and create an organization.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123",
  "org_name": "My Organization"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### POST /api/v1/auth/login

Authenticate user and return tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### POST /api/v1/auth/refresh

Get a new access token using a refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### POST /api/v1/auth/logout

Invalidate a refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (204):** No content

### GET /api/v1/auth/me

Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "org_id": "123e4567-e89b-12d3-a456-426614174001",
  "team_id": null,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Token Configuration

Configure token expiration times in `.env`:

```env
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Generate a secure secret key:**
```bash
openssl rand -hex 32
```

## Usage in Protected Routes

Use the `get_current_user` dependency to protect routes:

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_route(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"message": f"Hello {current_user.email}"}
```

## Security Features

### Password Hashing

- Uses bcrypt with automatic salt generation
- Passwords are never stored in plain text
- Password hashes are never returned in API responses

### Token Security

- Access tokens: Short-lived (default 30 minutes)
- Refresh tokens: Longer-lived (default 7 days)
- Tokens include type claim to prevent misuse
- Expired tokens are automatically rejected

### Token Invalidation

- Refresh tokens can be invalidated on logout
- Invalidated tokens are stored in Redis with TTL
- TTL matches token expiration time for automatic cleanup

### Error Handling

- Returns 401 (not 403) for missing/invalid tokens
- Generic error messages to prevent user enumeration
- Detailed logging for security monitoring

## Testing

### Manual Testing

Run the manual test script:

```bash
python server/test_auth_manual.py
```

### Unit Tests

Run the full test suite:

```bash
pytest server/tests/test_auth.py -v
```

### Test Coverage

The test suite covers:
- Password hashing and verification
- Token creation and decoding
- User registration (success and error cases)
- User login (success and error cases)
- Token refresh (success and error cases)
- Logout and token invalidation
- Protected endpoint access

## Error Responses

All authentication errors return consistent JSON format:

```json
{
  "detail": "Error message"
}
```

Common error codes:
- `400`: Bad request (e.g., email already registered)
- `401`: Unauthorized (invalid credentials, expired token)
- `422`: Validation error (invalid email format, short password)

## Best Practices

1. **Always use HTTPS in production** to protect tokens in transit
2. **Store tokens securely** on the client (httpOnly cookies or secure storage)
3. **Implement token refresh** before access token expires
4. **Logout on client** by discarding tokens and calling logout endpoint
5. **Monitor failed login attempts** for security threats
6. **Rotate secret keys** periodically in production
7. **Use strong passwords** (minimum 8 characters enforced)

## Dependencies

- `bcrypt>=4.1.0`: Password hashing
- `pyjwt>=2.8.0`: JWT token handling
- `fastapi`: Web framework
- `redis>=5.0.0`: Token invalidation storage
- `sqlalchemy>=2.0.25`: Database ORM

## Future Enhancements

Potential improvements for production:
- Email verification on registration
- Password reset flow
- Multi-factor authentication (MFA)
- Rate limiting on auth endpoints
- Account lockout after failed attempts
- OAuth2 integration (Google, GitHub, etc.)
- API key authentication for service accounts
- Session management and device tracking
