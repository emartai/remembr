"""Short-term session memory service backed by Redis sliding windows."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

import tiktoken
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Episode, Session
from app.services.cache import SHORT_TERM_TTL, CacheService, make_key
from app.services.scoping import MemoryScope


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

    def __init__(
        self,
        cache: CacheService,
        db: AsyncSession | None = None,
        max_tokens: int | None = None,
        auto_checkpoint_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        self.cache = cache
        self.db = db
        self.MAX_TOKENS = max_tokens or settings.short_term_max_tokens
        self.auto_checkpoint_threshold = (
            auto_checkpoint_threshold
            if auto_checkpoint_threshold is not None
            else settings.short_term_auto_checkpoint_threshold
        )
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def _key(self, session_id: str) -> str:
        return make_key("short_term", session_id, "window")

    @staticmethod
    def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    async def _get_scoped_session(self, session_id: str, scope: MemoryScope) -> Session:
        if self.db is None:
            raise ValueError("Database session is required for checkpoint operations")

        query = (
            select(Session)
            .where(Session.id == self._as_uuid(session_id))
            .where(Session.org_id == self._as_uuid(scope.org_id))
            .where(Session.team_id == self._as_uuid(scope.team_id))
            .where(Session.user_id == self._as_uuid(scope.user_id))
            .where(Session.agent_id == self._as_uuid(scope.agent_id))
        )
        result = await self.db.execute(query)
        scoped_session = result.scalar_one_or_none()
        if scoped_session is None:
            raise ValueError(f"Session not found in scope: {session_id}")
        return scoped_session

    async def _set_window_atomic(self, session_id: str, payload: list[dict]) -> None:
        key = self._key(session_id)
        serialized = json.dumps(payload)

        async with self.cache.redis.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            await pipe.setex(key, SHORT_TERM_TTL, serialized)
            await pipe.execute()

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

    def _compress_to_target(
        self,
        messages: list[SessionMessage],
        target_tokens: int,
    ) -> list[SessionMessage]:
        kept = list(messages)
        while sum(msg.tokens for msg in kept) > target_tokens and kept:
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

    async def checkpoint(self, session_id: str, scope: MemoryScope) -> str:
        """Persist current short-term window as a checkpoint episode."""
        scoped_session = await self._get_scoped_session(session_id, scope)
        current_messages = await self.get_context(session_id)

        payload = [
            {
                **asdict(msg),
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in current_messages
        ]

        episode = Episode(
            org_id=scoped_session.org_id,
            team_id=scoped_session.team_id,
            user_id=scoped_session.user_id,
            agent_id=scoped_session.agent_id,
            session_id=scoped_session.id,
            role="checkpoint",
            content=json.dumps(payload),
            metadata_={
                "checkpoint": True,
                "message_count": len(payload),
            },
        )
        self.db.add(episode)
        await self.db.flush()
        await self.db.refresh(episode)

        logger.info(
            "Short-term checkpoint created",
            session_id=session_id,
            checkpoint_id=str(episode.id),
            message_count=len(payload),
        )
        return str(episode.id)

    async def restore_from_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
        scope: MemoryScope,
    ) -> int:
        """Replace current window with messages restored from a checkpoint episode."""
        await self._get_scoped_session(session_id, scope)

        query = (
            select(Episode)
            .where(Episode.id == self._as_uuid(checkpoint_id))
            .where(Episode.session_id == self._as_uuid(session_id))
            .where(Episode.org_id == self._as_uuid(scope.org_id))
            .where(Episode.team_id == self._as_uuid(scope.team_id))
            .where(Episode.user_id == self._as_uuid(scope.user_id))
            .where(Episode.agent_id == self._as_uuid(scope.agent_id))
            .where(Episode.role == "checkpoint")
        )
        result = await self.db.execute(query)
        episode = result.scalar_one_or_none()
        if episode is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        restored_payload = json.loads(episode.content)
        await self._set_window_atomic(session_id, restored_payload)

        logger.info(
            "Short-term checkpoint restored",
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            restored_count=len(restored_payload),
        )
        return len(restored_payload)

    async def list_checkpoints(self, session_id: str, scope: MemoryScope) -> list[dict]:
        """List checkpoints available for a session in scope."""
        await self._get_scoped_session(session_id, scope)

        query = (
            select(Episode)
            .where(Episode.session_id == self._as_uuid(session_id))
            .where(Episode.org_id == self._as_uuid(scope.org_id))
            .where(Episode.team_id == self._as_uuid(scope.team_id))
            .where(Episode.user_id == self._as_uuid(scope.user_id))
            .where(Episode.agent_id == self._as_uuid(scope.agent_id))
            .where(Episode.role == "checkpoint")
            .order_by(desc(Episode.created_at))
        )
        result = await self.db.execute(query)
        episodes = list(result.scalars().all())

        return [
            {
                "checkpoint_id": str(episode.id),
                "created_at": episode.created_at,
                "message_count": int((episode.metadata_ or {}).get("message_count", 0)),
            }
            for episode in episodes
        ]

    async def auto_checkpoint(self, session_id: str, scope: MemoryScope) -> str | None:
        """Auto-checkpoint when token usage is above threshold and shrink window to 50%."""
        usage = await self.get_token_usage(session_id)
        threshold_pct = self.auto_checkpoint_threshold * 100
        if usage["percentage"] <= threshold_pct:
            return None

        checkpoint_id = await self.checkpoint(session_id, scope)
        messages = await self.get_context(session_id)
        target_tokens = int(self.MAX_TOKENS * 0.5)
        compressed = self._compress_to_target(messages, target_tokens=target_tokens)

        payload = [
            {
                **asdict(msg),
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in compressed
        ]
        await self.cache.set(self._key(session_id), payload, ttl_seconds=SHORT_TERM_TTL)

        logger.info(
            "Short-term auto-checkpoint complete",
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            original_tokens=usage["used"],
            compressed_tokens=sum(msg.tokens for msg in compressed),
        )
        return checkpoint_id

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
