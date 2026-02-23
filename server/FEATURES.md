# Remembr Server Features

## Application Factory Pattern

The server uses the factory pattern with `create_app()` to allow for:
- Easy testing with different configurations
- Multiple app instances with different settings
- Clean separation of concerns

```python
from app.main import create_app

app = create_app()
```

## Versioned API Routing

All API endpoints are versioned and mounted at `/api/v1/`:

```
GET /api/v1/health  -> Health check endpoint
```

Future versions can be added without breaking existing clients:
```
/api/v1/...  -> Version 1 endpoints
/api/v2/...  -> Version 2 endpoints (future)
```

## Request ID Tracking

Every request automatically gets a unique UUID that:
1. Is stored in `request.state.request_id`
2. Is added to all log entries for that request
3. Is returned in the `X-Request-ID` response header
4. Is included in all error responses

Example response headers:
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

## Structured JSON Logging

All logs are output in JSON format using loguru:

```json
{
  "timestamp": "2026-02-23T18:30:00.123456Z",
  "level": "INFO",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Request started",
  "method": "GET",
  "path": "/api/v1/health"
}
```

Log levels can be configured via the `LOG_LEVEL` environment variable.

## Global Exception Handling

All exceptions are caught and formatted consistently:

### HTTP Exceptions (404, 403, etc.)
```json
{
  "error": {
    "code": "HTTP_404",
    "message": "Not Found",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Validation Errors (422)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "details": [
      {
        "loc": ["body", "field_name"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

### Internal Server Errors (500)
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

Note: Stack traces are NEVER exposed in responses. They are only logged and sent to Sentry.

## CORS Configuration

CORS is automatically configured based on environment:
- **Local**: All origins allowed (`*`)
- **Staging/Production**: Restricted to specific origins (configure as needed)

## Sentry Integration

If `SENTRY_DSN` is configured, Sentry automatically:
- Captures all unhandled exceptions
- Includes request context (headers, body, etc.)
- Tracks performance with distributed tracing
- Groups errors intelligently

Sample rates:
- **Local**: 100% of traces
- **Staging/Production**: 10% of traces

## API Documentation

Interactive API documentation is available in non-production environments:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

In production, these endpoints are disabled for security.

## Middleware Stack

The middleware is applied in this order:

1. **CORS Middleware**: Handles cross-origin requests
2. **Request ID Middleware**: Generates and tracks request IDs
3. **Exception Handlers**: Catches and formats all errors

## Health Check

The health check endpoint provides:
- Service status
- Current environment
- API version

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

Use this endpoint for:
- Load balancer health checks
- Kubernetes liveness/readiness probes
- Monitoring systems
