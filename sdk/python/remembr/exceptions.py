"""SDK-specific exceptions for Remembr API errors."""

from __future__ import annotations

from typing import Any


class RemembrError(Exception):
    """Base SDK exception.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code when available.
        code: API error code when available.
        details: Additional API-provided metadata.
        request_id: Request identifier for support/debugging.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        self.request_id = request_id


class AuthenticationError(RemembrError):
    """Raised for authentication/authorization failures."""


class NotFoundError(RemembrError):
    """Raised when requested resource is not found."""


class RateLimitError(RemembrError):
    """Raised when the API rate limit is exceeded."""


class ServerError(RemembrError):
    """Raised for server-side or transient infrastructure failures."""
