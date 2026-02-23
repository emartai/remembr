"""Forgetting service for GDPR-compliant memory deletion workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import AsyncSessionLocal
from app.models import AuditLog, Embedding, Episode, Session
from app.services.cache import CacheService, make_key
from app.services.scoping import MemoryScope


@dataclass
class UserDeleteResult:
    deleted_episodes: int
    deleted_sessions: int


class ForgettingService:
    """Service for memory/session/user erasure with audit trails."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.session_factory = session_factory or AsyncSessionLocal

    @staticmethod
    def _scope_query_filters(scope: MemoryScope) -> dict[str, UUID | None]:
        return {
            "org_id": UUID(scope.org_id),
            "team_id": UUID(scope.team_id) if scope.team_id else None,
            "user_id": UUID(scope.user_id) if scope.user_id else None,
            "agent_id": UUID(scope.agent_id) if scope.agent_id else None,
        }

    async def _write_audit(
        self,
        *,
        action: str,
        status: str,
        target_type: str,
        target_id: str | None,
        request_id: str,
        actor_user_id: UUID | None,
        org_id: UUID | None,
        details: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            async with self.session_factory() as audit_db:
                audit_db.add(
                    AuditLog(
                        org_id=org_id,
                        actor_user_id=actor_user_id,
                        action=action,
                        status=status,
                        target_type=target_type,
                        target_id=target_id,
                        request_id=request_id,
                        details=details,
                        error_message=error_message,
                    )
                )
                await audit_db.commit()
        except Exception as exc:
            logger.error("Failed to persist audit log", action=action, error=str(exc))

    async def delete_episode(
        self,
        *,
        episode_id: UUID,
        scope: MemoryScope,
        request_id: str,
        actor_user_id: UUID | None,
    ) -> bool:
        try:
            async with self.db.begin():
                filters = self._scope_query_filters(scope)
                result = await self.db.execute(
                    select(Episode)
                    .where(Episode.id == episode_id)
                    .where(Episode.org_id == filters["org_id"])
                    .where(Episode.team_id == filters["team_id"])
                    .where(Episode.user_id == filters["user_id"])
                    .where(Episode.agent_id == filters["agent_id"])
                )
                episode = result.scalar_one_or_none()
                if episode is None:
                    return False

                await self.db.execute(delete(Embedding).where(Embedding.episode_id == episode_id))
                await self.db.delete(episode)

            await self._write_audit(
                action="delete_episode",
                status="success",
                target_type="episode",
                target_id=str(episode_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=filters["org_id"],
            )
            return True
        except Exception as exc:
            await self._write_audit(
                action="delete_episode",
                status="failed",
                target_type="episode",
                target_id=str(episode_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=UUID(scope.org_id),
                error_message=str(exc),
            )
            raise

    async def delete_session_memories(
        self,
        *,
        session_id: UUID,
        scope: MemoryScope,
        request_id: str,
        actor_user_id: UUID | None,
    ) -> int:
        filters = self._scope_query_filters(scope)
        try:
            async with self.db.begin():
                session_result = await self.db.execute(
                    select(Session)
                    .where(Session.id == session_id)
                    .where(Session.org_id == filters["org_id"])
                    .where(Session.team_id == filters["team_id"])
                    .where(Session.user_id == filters["user_id"])
                    .where(Session.agent_id == filters["agent_id"])
                )
                scoped_session = session_result.scalar_one_or_none()
                if scoped_session is None:
                    return 0

                count_result = await self.db.execute(
                    select(func.count(Episode.id)).where(Episode.session_id == session_id)
                )
                deleted_count = int(count_result.scalar_one())

                await self.db.execute(
                    delete(Embedding).where(
                        Embedding.episode_id.in_(
                            select(Episode.id).where(Episode.session_id == session_id)
                        )
                    )
                )
                await self.db.execute(delete(Episode).where(Episode.session_id == session_id))

                cache = CacheService(self.redis)
                await cache.delete(make_key("short_term", str(session_id), "window"))

            await self._write_audit(
                action="delete_session_memories",
                status="success",
                target_type="session",
                target_id=str(session_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=filters["org_id"],
                details={"deleted_count": deleted_count},
            )
            return deleted_count
        except Exception as exc:
            await self._write_audit(
                action="delete_session_memories",
                status="failed",
                target_type="session",
                target_id=str(session_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=UUID(scope.org_id),
                error_message=str(exc),
            )
            raise

    async def delete_user_memories(
        self,
        *,
        user_id: UUID,
        org_id: UUID,
        request_id: str,
        actor_user_id: UUID | None,
    ) -> UserDeleteResult:
        await self._write_audit(
            action="delete_user_memories",
            status="attempt",
            target_type="user",
            target_id=str(user_id),
            request_id=request_id,
            actor_user_id=actor_user_id,
            org_id=org_id,
        )

        try:
            async with self.db.begin():
                session_ids_result = await self.db.execute(
                    select(Session.id)
                    .where(Session.org_id == org_id)
                    .where(Session.user_id == user_id)
                )
                session_ids = [row[0] for row in session_ids_result.all()]

                episodes_count_result = await self.db.execute(
                    select(func.count(Episode.id))
                    .where(Episode.org_id == org_id)
                    .where(Episode.user_id == user_id)
                )
                deleted_episodes = int(episodes_count_result.scalar_one())

                deleted_sessions = len(session_ids)

                if session_ids:
                    await self.db.execute(
                        delete(Embedding).where(
                            Embedding.episode_id.in_(
                                select(Episode.id).where(Episode.session_id.in_(session_ids))
                            )
                        )
                    )

                await self.db.execute(
                    delete(Embedding)
                    .where(Embedding.org_id == org_id)
                    .where(
                        Embedding.episode_id.in_(
                            select(Episode.id)
                            .where(Episode.org_id == org_id)
                            .where(Episode.user_id == user_id)
                        )
                    )
                )

                await self.db.execute(
                    delete(Episode)
                    .where(Episode.org_id == org_id)
                    .where(Episode.user_id == user_id)
                )
                await self.db.execute(
                    delete(Session)
                    .where(Session.org_id == org_id)
                    .where(Session.user_id == user_id)
                )

            await self._write_audit(
                action="delete_user_memories",
                status="success",
                target_type="user",
                target_id=str(user_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=org_id,
                details={
                    "deleted_episodes": deleted_episodes,
                    "deleted_sessions": deleted_sessions,
                },
            )

            return UserDeleteResult(
                deleted_episodes=deleted_episodes,
                deleted_sessions=deleted_sessions,
            )
        except Exception as exc:
            await self._write_audit(
                action="delete_user_memories",
                status="failed",
                target_type="user",
                target_id=str(user_id),
                request_id=request_id,
                actor_user_id=actor_user_id,
                org_id=org_id,
                error_message=str(exc),
            )
            raise
