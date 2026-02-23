"""Short-term session memory service backed by Redis sliding windows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import tiktoken

from app.config import get_settings
from app.services.cache import SHORT_TERM_TTL, CacheService, make_key


@dataclass
class SessionMessage:
    """Message envelope persisted in short-term memory."""

    role: str
    content: str
    tokens: int
    priority_score: float
    timestamp: datetime


class ShortTermMemory:
    """Manage short-term conversational context in Redis."""

    _ROLE_WEIGHTS = {
        "system": 3.0,
        "user": 2.0,
        "assistant": 1.0,
    }

    def __init__(self, cache: CacheService, max_tokens: int | None = None) -> None:
        self.cache = cache
        self.MAX_TOKENS = max_tokens or get_settings().short_term_max_tokens
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def _key(self, session_id: str) -> str:
        return make_key("short_term", session_id, "window")

    def token_count(self, text: str) -> int:
        """Count text tokens using cl100k_base tokenizer."""
        return len(self._encoding.encode(text or ""))

    def _score_priority(self, message: SessionMessage) -> float:
        """Score message priority deterministically for compression decisions."""
        role_weight = self._ROLE_WEIGHTS.get(message.role, 0.5)
        recency_component = message.timestamp.timestamp() / 1_000_000_000
        length_component = 1 / max(message.tokens, 1)
        return round((role_weight * 100) + (recency_component * 10) + length_component, 8)

    def _compress_window(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        """Drop lowest-priority messages until total tokens fits the configured budget."""
        kept = list(messages)

        while sum(msg.tokens for msg in kept) > self.MAX_TOKENS and kept:
            removal_idx = min(
                range(len(kept)),
                key=lambda idx: (
                    kept[idx].priority_score,
                    kept[idx].timestamp.timestamp(),
                    idx,
                ),
            )
            kept.pop(removal_idx)

        return kept

    async def add_message(self, session_id: str, message: SessionMessage) -> None:
        """Add a message to the sliding window and compress if over token budget."""
        current = await self.get_context(session_id)

        if message.tokens <= 0:
            message.tokens = self.token_count(message.content)
        if message.priority_score <= 0:
            message.priority_score = self._score_priority(message)

        current.append(message)
        compressed = self._compress_window(current)

        payload = [
            {
                **asdict(msg),
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in compressed
        ]
        await self.cache.set(self._key(session_id), payload, ttl_seconds=SHORT_TERM_TTL)

    async def get_context(self, session_id: str) -> list[SessionMessage]:
        """Load the current short-term context window from Redis."""
        cached = await self.cache.get(self._key(session_id))
        if not cached:
            return []

        return [
            SessionMessage(
                role=item["role"],
                content=item["content"],
                tokens=int(item["tokens"]),
                priority_score=float(item["priority_score"]),
                timestamp=datetime.fromisoformat(item["timestamp"]),
            )
            for item in cached
        ]

    async def get_token_usage(self, session_id: str) -> dict[str, float]:
        """Return token utilization for the active context window."""
        messages = await self.get_context(session_id)
        used = sum(msg.tokens for msg in messages)
        percentage = (used / self.MAX_TOKENS * 100) if self.MAX_TOKENS else 0
        return {
            "used": used,
            "max": self.MAX_TOKENS,
            "percentage": round(percentage, 2),
        }

