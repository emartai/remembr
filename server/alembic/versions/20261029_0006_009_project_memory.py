"""Explicit project spaces and grants; legacy memories remain private."""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE memory_projects (\n\torg_id UUID NOT NULL, \n\towner_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(org_id) REFERENCES organizations (id), \n\tFOREIGN KEY(owner_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_memory_projects_org_id ON memory_projects (org_id)")
    op.execute(
        "\nCREATE TABLE memory_spaces (\n\torg_id UUID NOT NULL, \n\tproject_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(org_id) REFERENCES organizations (id), \n\tFOREIGN KEY(project_id) REFERENCES memory_projects (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_memory_spaces_org_id ON memory_spaces (org_id)")
    op.execute("CREATE INDEX ix_memory_spaces_project_id ON memory_spaces (project_id)")
    op.execute(
        "\nCREATE TABLE space_principals (\n\torg_id UUID NOT NULL, \n\tissuer_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tkey_hash VARCHAR(64) NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(org_id) REFERENCES organizations (id), \n\tFOREIGN KEY(issuer_id) REFERENCES users (id), \n\tUNIQUE (key_hash)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_space_principals_org_id ON space_principals (org_id)")
    op.execute(
        "\nCREATE TABLE space_grants (\n\tspace_id UUID NOT NULL, \n\tprincipal_id UUID NOT NULL, \n\tcan_read BOOLEAN NOT NULL, \n\tcan_write BOOLEAN NOT NULL, \n\tcan_delete BOOLEAN NOT NULL, \n\tPRIMARY KEY (space_id, principal_id), \n\tFOREIGN KEY(space_id) REFERENCES memory_spaces (id), \n\tFOREIGN KEY(principal_id) REFERENCES space_principals (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE project_memories (\n\torg_id UUID NOT NULL, \n\tspace_id UUID NOT NULL, \n\tauthor_id UUID NOT NULL, \n\tauthor_kind VARCHAR(16) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tsource_ref VARCHAR(2000), \n\trun_id VARCHAR(200), \n\tidempotency_key VARCHAR(160) NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\tsupersedes_id UUID, \n\tsuperseded_at TIMESTAMP WITH TIME ZONE, \n\texpires_at TIMESTAMP WITH TIME ZONE, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tembedding_status VARCHAR(16) NOT NULL, \n\tembedding_error VARCHAR(200), \n\tembedding_model VARCHAR(255), \n\tvector VECTOR, \n\tid UUID DEFAULT gen_random_uuid() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (space_id, author_id, idempotency_key), \n\tUNIQUE (supersedes_id), \n\tFOREIGN KEY(org_id) REFERENCES organizations (id), \n\tFOREIGN KEY(space_id) REFERENCES memory_spaces (id), \n\tFOREIGN KEY(supersedes_id) REFERENCES project_memories (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_project_memories_expires_at ON project_memories (expires_at)")
    op.execute("CREATE INDEX ix_project_memories_org_id ON project_memories (org_id)")
    op.execute("CREATE INDEX ix_project_memories_space_id ON project_memories (space_id)")
    op.execute("ALTER TABLE memory_projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_projects FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON memory_projects USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid) WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE memory_spaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_spaces FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON memory_spaces USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid) WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE project_memories ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE project_memories FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON project_memories USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid) WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)"
    )


def downgrade():
    op.drop_table("project_memories")
    op.drop_table("space_grants")
    op.drop_table("space_principals")
    op.drop_table("memory_spaces")
    op.drop_table("memory_projects")
