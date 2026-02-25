"""Standard API response helpers and schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    data: T
    request_id: str
    timestamp: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


def success(data: T, request_id: str) -> StandardResponse[T]:
    return StandardResponse(
        data=data,
        request_id=request_id,
        timestamp=datetime.now(datetime.UTC).isoformat(),
    )


def error(
    code: str,
    message: str,
    status_code: int,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())
