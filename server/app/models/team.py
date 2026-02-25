from __future__ import annotations

"""Team model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class Team(Base, UUIDMixin):
    """
    Team model for grouping users within an organization.
    """

    __tablename__ = "teams"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="teams",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="team",
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="team",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="team",
    )
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="team",
    )
    memory_facts: Mapped[list["MemoryFact"]] = relationship(
        "MemoryFact",
        back_populates="team",
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, org_id={self.org_id})>"

