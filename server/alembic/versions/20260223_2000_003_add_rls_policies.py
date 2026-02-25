"""Add Row-Level Security policies for multi-tenancy

Revision ID: 003
Revises: 002
Create Date: 2026-02-23 20:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Enable Row-Level Security on multi-tenant tables.

    RLS provides a database-level safety net for multi-tenancy.
    Even if application code has a bug, the database will prevent
    cross-organization data access.
    """

    # Enable RLS on sessions table
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")

    # Create policy for sessions
    op.execute("""
        CREATE POLICY sessions_org_isolation ON sessions
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
    """)

    # Enable RLS on episodes table
    op.execute("ALTER TABLE episodes ENABLE ROW LEVEL SECURITY")

    # Create policy for episodes
    op.execute("""
        CREATE POLICY episodes_org_isolation ON episodes
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
    """)

    # Enable RLS on memory_facts table
    op.execute("ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY")

    # Create policy for memory_facts
    op.execute("""
        CREATE POLICY memory_facts_org_isolation ON memory_facts
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
    """)

    # Enable RLS on embeddings table
    op.execute("ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY")

    # Create policy for embeddings
    op.execute("""
        CREATE POLICY embeddings_org_isolation ON embeddings
        USING (org_id = current_setting('app.current_org_id', true)::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid)
    """)


def downgrade() -> None:
    """Remove RLS policies and disable RLS."""

    # Drop policies
    op.execute("DROP POLICY IF EXISTS sessions_org_isolation ON sessions")
    op.execute("DROP POLICY IF EXISTS episodes_org_isolation ON episodes")
    op.execute("DROP POLICY IF EXISTS memory_facts_org_isolation ON memory_facts")
    op.execute("DROP POLICY IF EXISTS embeddings_org_isolation ON embeddings")

    # Disable RLS
    op.execute("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE episodes DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_facts DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE embeddings DISABLE ROW LEVEL SECURITY")
