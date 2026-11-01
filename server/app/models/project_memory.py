"""Explicitly shared memory. Legacy episodes are never migrated into these tables."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class Project(Base, UUIDMixin):
    __tablename__ = "memory_projects"
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemorySpace(Base, UUIDMixin):
    __tablename__ = "memory_spaces"
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memory_projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpacePrincipal(Base, UUIDMixin):
    __tablename__ = "space_principals"
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    issuer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpaceGrant(Base):
    __tablename__ = "space_grants"
    space_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memory_spaces.id"), primary_key=True)
    principal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("space_principals.id"), primary_key=True
    )
    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectMemory(Base, UUIDMixin):
    __tablename__ = "project_memories"
    __table_args__ = (
        UniqueConstraint("space_id", "author_id", "idempotency_key"),
        UniqueConstraint("supersedes_id"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    space_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memory_spaces.id"), index=True)
    # Stable authenticated identity; labels submitted in source_ref are only client claims.
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    author_kind: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String(2000))
    run_id: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    payload_hash: Mapped[str] = mapped_column(String(64))
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("project_memories.id"))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    embedding_status: Mapped[str] = mapped_column(String(16), default="pending")
    embedding_error: Mapped[str | None] = mapped_column(String(200))
    embedding_model: Mapped[str | None] = mapped_column(String(255))
    vector: Mapped[list[float] | None] = mapped_column(Vector())
