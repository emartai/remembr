"""Pydantic models used by the Remembr Python SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Session(BaseModel):
    request_id: str
    session_id: str
    org_id: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class Episode(BaseModel):
    episode_id: str
    session_id: str | None = None
    role: str
    content: str
    created_at: datetime
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class SearchResult(BaseModel):
    episode_id: str
    content: str
    role: str
    score: float
    created_at: datetime
    tags: list[str] = Field(default_factory=list)


class MemoryQueryResult(BaseModel):
    request_id: str
    results: list[SearchResult]
    total: int
    query_time_ms: int


class CheckpointInfo(BaseModel):
    checkpoint_id: str
    created_at: datetime
    message_count: int
