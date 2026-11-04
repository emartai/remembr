"""Remove the legacy dimension-pinned HNSW index without changing stored vectors.

Revision 005 relaxed the column's typmod, but PostgreSQL retained the original
1024-dimensional HNSW index. Inserts from the default 768-dimensional Ollama
model still failed in that index. Variable-dimension storage uses exact search;
future ANN indexes must be scoped to a model and dimension explicitly.
"""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_cosine")


def downgrade() -> None:
    # Restore a 1024-dimensional index without rejecting already stored vectors
    # from other providers or narrowing the variable-dimension column again.
    op.execute(
        "CREATE INDEX ix_embeddings_vector_cosine ON embeddings "
        "USING hnsw ((vector::vector(1024)) vector_cosine_ops) "
        "WHERE vector_dims(vector) = 1024"
    )
