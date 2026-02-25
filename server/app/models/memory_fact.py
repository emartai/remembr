from __future__ import annotations

"""Memory Fact model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class MemoryFact(Base, UUIDMixin, TimestampMixin):
    """
    Memory Fact model using subject-predicate-object triples.

    Represents extracted knowledge from episodes with temporal validity.
    """

    __tablename__ = "memory_facts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_episode_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("episodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memory_facts",
    )
    team: Mapped["Team | None"] = relationship(
        "Team",
        back_populates="memory_facts",
    )
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="memory_facts",
    )
    agent: Mapped["Agent | None"] = relationship(
        "Agent",
        back_populates="memory_facts",
    )
    source_episode: Mapped["Episode | None"] = relationship(
        "Episode",
        back_populates="memory_facts",
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding",
        back_populates="memory_fact",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<MemoryFact(id={self.id}, "
            f"subject={self.subject[:20]}, "
            f"predicate={self.predicate[:20]}, "
            f"org_id={self.org_id})>"
        )

