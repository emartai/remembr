"""Tests for memory scoping system.

These are pure unit tests that don't require database or Redis.
"""

import uuid

import pytest

from app.middleware.context import RequestContext
from app.services.scoping import MemoryScope, ScopeResolver


class TestMemoryScope:
    """Tests for MemoryScope dataclass."""

    def test_org_scope_creation(self):
        """Test creating an org-level scope."""
        org_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, level="org")
        
        assert scope.org_id == org_id
        assert scope.team_id is None
        assert scope.user_id is None
        assert scope.agent_id is None
        assert scope.level == "org"

    def test_team_scope_creation(self):
        """Test creating a team-level scope."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, team_id=team_id, level="team")
        
        assert scope.org_id == org_id
        assert scope.team_id == team_id
        assert scope.user_id is None
        assert scope.agent_id is None
        assert scope.level == "team"

    def test_user_scope_creation(self):
        """Test creating a user-level scope."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            level="user",
        )
        
        assert scope.org_id == org_id
        assert scope.team_id == team_id
        assert scope.user_id == user_id
        assert scope.agent_id is None
        assert scope.level == "user"

    def test_agent_scope_creation(self):
        """Test creating an agent-level scope."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        assert scope.org_id == org_id
        assert scope.team_id == team_id
        assert scope.user_id == user_id
        assert scope.agent_id == agent_id
        assert scope.level == "agent"

    def test_agent_scope_requires_agent_id(self):
        """Test that agent-level scope requires agent_id."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="agent_id required"):
            MemoryScope(
                org_id=org_id,
                user_id=user_id,
                level="agent",
            )

    def test_user_scope_requires_user_id(self):
        """Test that user-level scope requires user_id."""
        org_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="user_id required"):
            MemoryScope(org_id=org_id, level="user")

    def test_team_scope_requires_team_id(self):
        """Test that team-level scope requires team_id."""
        org_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="team_id required"):
            MemoryScope(org_id=org_id, level="team")

    def test_agent_scope_requires_user_id(self):
        """Test that agent scope requires user_id (hierarchy consistency)."""
        org_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="user_id required"):
            MemoryScope(
                org_id=org_id,
                agent_id=agent_id,
                level="agent",
            )


class TestScopeResolver:
    """Tests for ScopeResolver class."""

    def test_from_request_context_org_level(self):
        """Test building scope from org-level request context."""
        org_id = uuid.uuid4()
        ctx = RequestContext(
            request_id="test-123",
            org_id=org_id,
            user_id=None,
            agent_id=None,
            auth_method="api_key",
        )
        
        scope = ScopeResolver.from_request_context(ctx)
        
        assert scope.org_id == org_id
        assert scope.user_id is None
        assert scope.agent_id is None
        assert scope.level == "org"

    def test_from_request_context_user_level(self):
        """Test building scope from user-level request context."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ctx = RequestContext(
            request_id="test-123",
            org_id=org_id,
            user_id=user_id,
            agent_id=None,
            auth_method="jwt",
        )
        
        scope = ScopeResolver.from_request_context(ctx)
        
        assert scope.org_id == org_id
        assert scope.user_id == user_id
        assert scope.agent_id is None
        assert scope.level == "user"

    def test_from_request_context_agent_level(self):
        """Test building scope from agent-level request context."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        ctx = RequestContext(
            request_id="test-123",
            org_id=org_id,
            user_id=user_id,
            agent_id=agent_id,
            auth_method="api_key",
        )
        
        scope = ScopeResolver.from_request_context(ctx)
        
        assert scope.org_id == org_id
        assert scope.user_id == user_id
        assert scope.agent_id == agent_id
        assert scope.level == "agent"

    def test_resolve_readable_scopes_org_level(self):
        """Test that org-level scope can only read org memories."""
        org_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, level="org")
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        assert len(readable) == 1
        assert readable[0].level == "org"
        assert readable[0].org_id == org_id
        assert readable[0].team_id is None
        assert readable[0].user_id is None
        assert readable[0].agent_id is None

    def test_resolve_readable_scopes_team_level(self):
        """Test that team-level scope can read team + org memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, team_id=team_id, level="team")
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        assert len(readable) == 2
        
        # Check team scope
        team_scope = next(s for s in readable if s.level == "team")
        assert team_scope.org_id == org_id
        assert team_scope.team_id == team_id
        assert team_scope.user_id is None
        assert team_scope.agent_id is None
        
        # Check org scope
        org_scope = next(s for s in readable if s.level == "org")
        assert org_scope.org_id == org_id
        assert org_scope.team_id is None
        assert org_scope.user_id is None
        assert org_scope.agent_id is None

    def test_resolve_readable_scopes_user_level(self):
        """Test that user-level scope can read user + team + org memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            level="user",
        )
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        assert len(readable) == 3
        
        # Check user scope
        user_scope = next(s for s in readable if s.level == "user")
        assert user_scope.org_id == org_id
        assert user_scope.team_id == team_id
        assert user_scope.user_id == user_id
        assert user_scope.agent_id is None
        
        # Check team scope
        team_scope = next(s for s in readable if s.level == "team")
        assert team_scope.org_id == org_id
        assert team_scope.team_id == team_id
        assert team_scope.user_id is None
        assert team_scope.agent_id is None
        
        # Check org scope
        org_scope = next(s for s in readable if s.level == "org")
        assert org_scope.org_id == org_id
        assert org_scope.team_id is None
        assert org_scope.user_id is None
        assert org_scope.agent_id is None

    def test_resolve_readable_scopes_user_level_without_team(self):
        """Test that user-level scope without team can read user + org memories."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            user_id=user_id,
            level="user",
        )
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # Should have user and org scopes (no team)
        assert len(readable) == 2
        
        levels = [s.level for s in readable]
        assert "user" in levels
        assert "org" in levels
        assert "team" not in levels

    def test_resolve_readable_scopes_agent_level(self):
        """Test that agent-level scope can read agent + user + team + org memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        assert len(readable) == 4
        
        # Check agent scope
        agent_scope = next(s for s in readable if s.level == "agent")
        assert agent_scope.org_id == org_id
        assert agent_scope.team_id == team_id
        assert agent_scope.user_id == user_id
        assert agent_scope.agent_id == agent_id
        
        # Check user scope
        user_scope = next(s for s in readable if s.level == "user")
        assert user_scope.org_id == org_id
        assert user_scope.team_id == team_id
        assert user_scope.user_id == user_id
        assert user_scope.agent_id is None
        
        # Check team scope
        team_scope = next(s for s in readable if s.level == "team")
        assert team_scope.org_id == org_id
        assert team_scope.team_id == team_id
        assert team_scope.user_id is None
        assert team_scope.agent_id is None
        
        # Check org scope
        org_scope = next(s for s in readable if s.level == "org")
        assert org_scope.org_id == org_id
        assert org_scope.team_id is None
        assert org_scope.user_id is None
        assert org_scope.agent_id is None

    def test_resolve_readable_scopes_agent_level_without_team(self):
        """Test that agent-level scope without team can read agent + user + org."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # Should have agent, user, and org scopes (no team)
        assert len(readable) == 3
        
        levels = [s.level for s in readable]
        assert "agent" in levels
        assert "user" in levels
        assert "org" in levels
        assert "team" not in levels

    def test_user_cannot_read_agent_private_memories(self):
        """Test that user-level scope does NOT include agent-private memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            level="user",
        )
        
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # User should NOT have agent-level scope
        levels = [s.level for s in readable]
        assert "agent" not in levels
        assert "user" in levels
        assert "team" in levels
        assert "org" in levels

    def test_resolve_writable_scope_returns_same_scope(self):
        """Test that writable scope returns the input scope (most specific)."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        writable = ScopeResolver.resolve_writable_scope(scope)
        
        assert writable.org_id == org_id
        assert writable.team_id == team_id
        assert writable.user_id == user_id
        assert writable.agent_id == agent_id
        assert writable.level == "agent"


class TestSQLFilterGeneration:
    """Tests for SQL filter generation."""

    def test_to_sql_filter_empty_scopes(self):
        """Test that empty scopes list returns False (no access)."""
        # Mock columns
        from sqlalchemy import Column, Integer
        
        org_col = Column("org_id", Integer)
        team_col = Column("team_id", Integer)
        user_col = Column("user_id", Integer)
        agent_col = Column("agent_id", Integer)
        
        filter_clause = ScopeResolver.to_sql_filter(
            [],
            org_col,
            team_col,
            user_col,
            agent_col,
        )
        
        # Should return False (no access)
        assert filter_clause is False

    def test_to_sql_filter_org_scope(self):
        """Test SQL filter for org-level scope."""
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        
        org_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, level="org")
        
        # Mock columns
        org_col = Column("org_id", UUID(as_uuid=True))
        team_col = Column("team_id", UUID(as_uuid=True))
        user_col = Column("user_id", UUID(as_uuid=True))
        agent_col = Column("agent_id", UUID(as_uuid=True))
        
        filter_clause = ScopeResolver.to_sql_filter(
            [scope],
            org_col,
            team_col,
            user_col,
            agent_col,
        )
        
        # Should generate: org_id = X AND team_id IS NULL AND user_id IS NULL AND agent_id IS NULL
        assert filter_clause is not None
        # The filter is an OR clause with one AND clause inside
        assert hasattr(filter_clause, "clauses")

    def test_to_sql_filter_multiple_scopes(self):
        """Test SQL filter for multiple scopes (agent can read all levels)."""
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        
        agent_scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        readable_scopes = ScopeResolver.resolve_readable_scopes(agent_scope)
        
        # Mock columns
        org_col = Column("org_id", UUID(as_uuid=True))
        team_col = Column("team_id", UUID(as_uuid=True))
        user_col = Column("user_id", UUID(as_uuid=True))
        agent_col = Column("agent_id", UUID(as_uuid=True))
        
        filter_clause = ScopeResolver.to_sql_filter(
            readable_scopes,
            org_col,
            team_col,
            user_col,
            agent_col,
        )
        
        # Should generate an OR clause with 4 AND clauses (agent, user, team, org)
        assert filter_clause is not None
        assert hasattr(filter_clause, "clauses")
        # Should have 4 clauses (one for each level)
        assert len(filter_clause.clauses) == 4

    def test_to_sql_filter_user_scope_excludes_agent(self):
        """Test that user-level filter does NOT include agent-private memories."""
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        user_scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            level="user",
        )
        
        readable_scopes = ScopeResolver.resolve_readable_scopes(user_scope)
        
        # Mock columns
        org_col = Column("org_id", UUID(as_uuid=True))
        team_col = Column("team_id", UUID(as_uuid=True))
        user_col = Column("user_id", UUID(as_uuid=True))
        agent_col = Column("agent_id", UUID(as_uuid=True))
        
        filter_clause = ScopeResolver.to_sql_filter(
            readable_scopes,
            org_col,
            team_col,
            user_col,
            agent_col,
        )
        
        # Should generate an OR clause with 3 AND clauses (user, team, org - NO agent)
        assert filter_clause is not None
        assert hasattr(filter_clause, "clauses")
        # Should have 3 clauses (user, team, org)
        assert len(filter_clause.clauses) == 3


class TestScopeInheritanceRules:
    """Integration tests for scope inheritance rules."""

    def test_agent_can_read_all_levels(self):
        """Test that agent-scoped request can read org, team, user, and agent memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        
        # Create agent scope
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        # Resolve readable scopes
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # Agent should be able to read all 4 levels
        levels = {s.level for s in readable}
        assert levels == {"agent", "user", "team", "org"}
        
        # Verify each scope has correct IDs
        agent_scope = next(s for s in readable if s.level == "agent")
        assert agent_scope.agent_id == agent_id
        assert agent_scope.user_id == user_id
        assert agent_scope.team_id == team_id
        
        user_scope = next(s for s in readable if s.level == "user")
        assert user_scope.agent_id is None
        assert user_scope.user_id == user_id
        assert user_scope.team_id == team_id
        
        team_scope = next(s for s in readable if s.level == "team")
        assert team_scope.agent_id is None
        assert team_scope.user_id is None
        assert team_scope.team_id == team_id
        
        org_scope = next(s for s in readable if s.level == "org")
        assert org_scope.agent_id is None
        assert org_scope.user_id is None
        assert org_scope.team_id is None

    def test_user_cannot_read_agent_private(self):
        """Test that user-scoped request cannot read agent-private memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Create user scope
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            level="user",
        )
        
        # Resolve readable scopes
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # User should be able to read user, team, org (NOT agent)
        levels = {s.level for s in readable}
        assert levels == {"user", "team", "org"}
        assert "agent" not in levels

    def test_team_can_read_team_and_org(self):
        """Test that team-scoped request can read team and org memories."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        
        # Create team scope
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            level="team",
        )
        
        # Resolve readable scopes
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # Team should be able to read team and org
        levels = {s.level for s in readable}
        assert levels == {"team", "org"}

    def test_org_can_only_read_org(self):
        """Test that org-scoped request can only read org memories."""
        org_id = uuid.uuid4()
        
        # Create org scope
        scope = MemoryScope(org_id=org_id, level="org")
        
        # Resolve readable scopes
        readable = ScopeResolver.resolve_readable_scopes(scope)
        
        # Org should only be able to read org
        levels = {s.level for s in readable}
        assert levels == {"org"}

    def test_scope_determinism(self):
        """Test that scope resolution is deterministic."""
        org_id = uuid.uuid4()
        team_id = uuid.uuid4()
        user_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        
        scope = MemoryScope(
            org_id=org_id,
            team_id=team_id,
            user_id=user_id,
            agent_id=agent_id,
            level="agent",
        )
        
        # Resolve multiple times
        readable1 = ScopeResolver.resolve_readable_scopes(scope)
        readable2 = ScopeResolver.resolve_readable_scopes(scope)
        
        # Should be identical
        assert len(readable1) == len(readable2)
        
        levels1 = [s.level for s in readable1]
        levels2 = [s.level for s in readable2]
        assert levels1 == levels2
