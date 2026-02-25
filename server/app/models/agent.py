from __future__ import annotations

"""Agent model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class Agent(Base, UUIDMixin):
    """
    Agent model representing AI agents that use the memory system.
    """

    __tablename__ = "agents"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="agents",
    )
    team: Mapped["Team | None"] = relationship(
        "Team",
        back_populates="agents",
    )
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="agents",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="agent",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="agent",
    )
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="agent",
    )
    memory_facts: Mapped[list["MemoryFact"]] = relationship(
        "MemoryFact",
        back_populates="agent",
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, org_id={self.org_id})>"
