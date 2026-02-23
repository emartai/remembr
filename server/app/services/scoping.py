"""Memory scoping system for four-level hierarchy (org → team → user → agent)."""

import uuid
from dataclasses import dataclass
from typing import Literal

from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.sql import ColumnElement

from app.middleware.context import RequestContext


@dataclass
class MemoryScope:
    """
    Represents a memory scope at one of four levels: org, team, user, or agent.
    
    The scope hierarchy is:
    - org: Organization-wide memories (accessible to all)
    - team: Team-scoped memories (accessible to team members)
    - user: User-scoped memories (accessible to user and their agents)
    - agent: Agent-private memories (accessible only to that specific agent)
    
    Attributes:
        org_id: Organization ID (always required)
        team_id: Team ID (optional, required for team/user/agent levels)
        user_id: User ID (optional, required for user/agent levels)
        agent_id: Agent ID (optional, required for agent level)
        level: The scope level (org, team, user, or agent)
    """

    org_id: uuid.UUID
    team_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    level: Literal["org", "team", "user", "agent"] = "org"

    def __post_init__(self) -> None:
        """Validate scope consistency."""
        # Validate level matches provided IDs
        if self.level == "agent" and not self.agent_id:
            raise ValueError("agent_id required for agent-level scope")
        if self.level == "user" and not self.user_id:
            raise ValueError("user_id required for user-level scope")
        if self.level == "team" and not self.team_id:
            raise ValueError("team_id required for team-level scope")
        
        # Validate hierarchy consistency
        if self.agent_id and not self.user_id:
            raise ValueError("user_id required when agent_id is set")
        if self.user_id and not self.team_id:
            # User can exist without team, but if they have a team, it should be set
            pass

    def __repr__(self) -> str:
        return (
            f"MemoryScope(level={self.level}, org_id={self.org_id}, "
            f"team_id={self.team_id}, user_id={self.user_id}, agent_id={self.agent_id})"
        )


class ScopeResolver:
    """
    Resolves memory scopes for read/write operations with inheritance rules.
    
    Inheritance rules:
    - Agent scope can read: agent + user + team + org memories
    - User scope can read: user + team + org memories (NOT agent-private)
    - Team scope can read: team + org memories
    - Org scope can read: org memories only
    
    Write operations always write at the most specific level available.
    """

    @staticmethod
    def from_request_context(ctx: RequestContext) -> MemoryScope:
        """
        Build a MemoryScope from a RequestContext.
        
        Determines the most specific scope level based on available context.
        
        Args:
            ctx: Request context containing authentication info
            
        Returns:
            MemoryScope at the most specific level available
        """
        # Determine the most specific level
        if ctx.agent_id:
            level = "agent"
        elif ctx.user_id:
            level = "user"
        else:
            # If no user_id, we're at org level
            # (team_id without user_id doesn't make sense in our auth model)
            level = "org"
        
        # Note: team_id is not directly in RequestContext, but would be
        # fetched from the user's team relationship if needed
        scope = MemoryScope(
            org_id=ctx.org_id,
            team_id=None,  # Will be populated by caller if needed
            user_id=ctx.user_id,
            agent_id=ctx.agent_id,
            level=level,
        )
        
        logger.debug(
            "Built memory scope from request context",
            scope_level=scope.level,
            org_id=str(scope.org_id),
            user_id=str(scope.user_id) if scope.user_id else None,
            agent_id=str(scope.agent_id) if scope.agent_id else None,
        )
        
        return scope

    @staticmethod
    def resolve_readable_scopes(scope: MemoryScope) -> list[MemoryScope]:
        """
        Resolve all scopes readable from the given scope (inheritance).
        
        Implements the inheritance hierarchy:
        - agent → can read agent + user + team + org
        - user → can read user + team + org (NOT agent-private)
        - team → can read team + org
        - org → can read org only
        
        Args:
            scope: The scope to resolve readable scopes for
            
        Returns:
            List of MemoryScope objects representing all readable scopes
        """
        scopes: list[MemoryScope] = []
        
        if scope.level == "agent":
            # Agent can read its own memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=scope.team_id,
                    user_id=scope.user_id,
                    agent_id=scope.agent_id,
                    level="agent",
                )
            )
            
            # Agent can read user memories
            if scope.user_id:
                scopes.append(
                    MemoryScope(
                        org_id=scope.org_id,
                        team_id=scope.team_id,
                        user_id=scope.user_id,
                        agent_id=None,
                        level="user",
                    )
                )
            
            # Agent can read team memories
            if scope.team_id:
                scopes.append(
                    MemoryScope(
                        org_id=scope.org_id,
                        team_id=scope.team_id,
                        user_id=None,
                        agent_id=None,
                        level="team",
                    )
                )
            
            # Agent can read org memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=None,
                    user_id=None,
                    agent_id=None,
                    level="org",
                )
            )
        
        elif scope.level == "user":
            # User can read their own memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=scope.team_id,
                    user_id=scope.user_id,
                    agent_id=None,
                    level="user",
                )
            )
            
            # User can read team memories
            if scope.team_id:
                scopes.append(
                    MemoryScope(
                        org_id=scope.org_id,
                        team_id=scope.team_id,
                        user_id=None,
                        agent_id=None,
                        level="team",
                    )
                )
            
            # User can read org memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=None,
                    user_id=None,
                    agent_id=None,
                    level="org",
                )
            )
        
        elif scope.level == "team":
            # Team can read team memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=scope.team_id,
                    user_id=None,
                    agent_id=None,
                    level="team",
                )
            )
            
            # Team can read org memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=None,
                    user_id=None,
                    agent_id=None,
                    level="org",
                )
            )
        
        elif scope.level == "org":
            # Org can only read org memories
            scopes.append(
                MemoryScope(
                    org_id=scope.org_id,
                    team_id=None,
                    user_id=None,
                    agent_id=None,
                    level="org",
                )
            )
        
        logger.debug(
            "Resolved readable scopes",
            input_level=scope.level,
            readable_count=len(scopes),
            readable_levels=[s.level for s in scopes],
        )
        
        return scopes

    @staticmethod
    def resolve_writable_scope(scope: MemoryScope) -> MemoryScope:
        """
        Resolve the scope to write at (most specific level available).
        
        Write operations always write at the most specific level:
        - If agent_id is set → write at agent level
        - Else if user_id is set → write at user level
        - Else if team_id is set → write at team level
        - Else → write at org level
        
        Args:
            scope: The scope to resolve writable scope for
            
        Returns:
            MemoryScope representing where to write
        """
        # Return the scope as-is since it's already at the most specific level
        logger.debug(
            "Resolved writable scope",
            level=scope.level,
            org_id=str(scope.org_id),
        )
        
        return scope

    @staticmethod
    def to_sql_filter(
        scopes: list[MemoryScope],
        org_id_col: ColumnElement,
        team_id_col: ColumnElement,
        user_id_col: ColumnElement,
        agent_id_col: ColumnElement,
    ) -> ColumnElement:
        """
        Build a SQLAlchemy WHERE clause for filtering by multiple scopes.
        
        Creates an OR filter that matches any of the provided scopes.
        Each scope is matched by checking that all its fields match.
        
        Args:
            scopes: List of scopes to filter by
            org_id_col: SQLAlchemy column for org_id
            team_id_col: SQLAlchemy column for team_id
            user_id_col: SQLAlchemy column for user_id
            agent_id_col: SQLAlchemy column for agent_id
            
        Returns:
            SQLAlchemy WHERE clause (ColumnElement)
        """
        if not scopes:
            # No scopes means no access
            return False  # type: ignore
        
        conditions = []
        
        for scope in scopes:
            # Build conditions for this scope
            scope_conditions = [org_id_col == scope.org_id]
            
            if scope.level == "org":
                # Org-level: match org_id and all other fields are NULL
                scope_conditions.extend([
                    team_id_col.is_(None),
                    user_id_col.is_(None),
                    agent_id_col.is_(None),
                ])
            
            elif scope.level == "team":
                # Team-level: match org_id and team_id, user_id and agent_id are NULL
                scope_conditions.extend([
                    team_id_col == scope.team_id,
                    user_id_col.is_(None),
                    agent_id_col.is_(None),
                ])
            
            elif scope.level == "user":
                # User-level: match org_id, team_id (if set), user_id, agent_id is NULL
                if scope.team_id:
                    scope_conditions.append(team_id_col == scope.team_id)
                else:
                    scope_conditions.append(team_id_col.is_(None))
                
                scope_conditions.extend([
                    user_id_col == scope.user_id,
                    agent_id_col.is_(None),
                ])
            
            elif scope.level == "agent":
                # Agent-level: match all fields
                if scope.team_id:
                    scope_conditions.append(team_id_col == scope.team_id)
                else:
                    scope_conditions.append(team_id_col.is_(None))
                
                scope_conditions.extend([
                    user_id_col == scope.user_id,
                    agent_id_col == scope.agent_id,
                ])
            
            # Combine conditions for this scope with AND
            conditions.append(and_(*scope_conditions))
        
        # Combine all scope conditions with OR
        filter_clause = or_(*conditions)
        
        logger.debug(
            "Built SQL filter for scopes",
            scope_count=len(scopes),
            scope_levels=[s.level for s in scopes],
        )
        
        return filter_clause
