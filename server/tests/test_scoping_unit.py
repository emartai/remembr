"""Unit tests for memory scoping system (no database/Redis required)."""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid

import pytest


# Import after path setup
from app.middleware.context import RequestContext
from app.services.scoping import MemoryScope, ScopeResolver


class TestMemoryScope:
    """Tests for MemoryScope dataclass."""

    def test_org_scope_creation(self):
        """Test creating an org-level scope."""
        org_id = uuid.uuid4()
        scope = MemoryScope(org_id=org_id, level="org")
        
  