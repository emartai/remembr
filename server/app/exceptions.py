"""Custom application exceptions mapped to API errors."""

from __future__ import annotations

from typing import Any


class RemembrException(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(RemembrException):
    status_code = 404
    code = "NOT_FOUND"


class AuthenticationError(RemembrException):
    status_code = 401
    code = "AUTHENTICATION_ERROR"


class AuthorizationError(RemembrException):
    status_code = 403
    code = "AUTHORIZATION_ERROR"


class ValidationError(RemembrException):
    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(RemembrException):
    status_code = 409
    code = "CONFLICT_ERROR"


class RateLimitError(RemembrException):
    status_code = 429
    code = "RATE_LIMIT_ERROR"
