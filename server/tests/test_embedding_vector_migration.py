"""Reproduce the actual pre-010 pgvector index and retain mixed-dimension data."""

import importlib.util
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_fixed_index_migration_preserves_vectors_and_allows_local_models(db):
    schema = "migration_" + uuid.uuid4().hex
    await db.execute(text(f'CREATE SCHEMA "{schema}"'))
    await db.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
    await db.execute(text("CREATE TABLE embeddings (id integer PRIMARY KEY, vector vector(1024))"))
    await db.execute(
        text(
            "CREATE INDEX ix_embeddings_vector_cosine ON embeddings USING hnsw (vector vector_cosine_ops)"
        )
    )
    # Match revision 005: widening the column alone did not reset the index.
    await db.execute(text("ALTER TABLE embeddings ALTER COLUMN vector TYPE vector"))

    async def insert(identifier, dimensions):
        vector = "[" + ",".join(["0.1"] * dimensions) + "]"
        await db.execute(
            text("INSERT INTO embeddings VALUES (:id, CAST(:vector AS vector))"),
            {"id": identifier, "vector": vector},
        )

    await insert(1, 1024)
    original = await db.scalar(text("SELECT vector::text FROM embeddings WHERE id = 1"))
    # pgvector versions report this index mismatch using either wording.
    with pytest.raises(
        DBAPIError, match="expected 1024 dimensions|different vector dimensions 768 and 1024"
    ):
        async with db.begin_nested():
            await insert(2, 768)

    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/20261104_0007_010_drop_fixed_embedding_index.py"
    )
    spec = importlib.util.spec_from_file_location("vector_index_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    connection = await db.connection()

    def run(conn, direction):
        with Operations.context(MigrationContext.configure(conn)):
            getattr(migration, direction)()

    await connection.run_sync(run, "upgrade")
    await insert(2, 768)
    await insert(3, 384)
    assert await db.scalar(text("SELECT vector::text FROM embeddings WHERE id = 1")) == original
    rows = await db.execute(text("SELECT id, vector_dims(vector) FROM embeddings ORDER BY id"))
    assert [tuple(row) for row in rows] == [(1, 1024), (2, 768), (3, 384)]

    # A rollback must preserve the new providers' vectors too.
    await connection.run_sync(run, "downgrade")
    await insert(4, 768)
    await insert(5, 1024)
    assert await db.scalar(text("SELECT count(*) FROM embeddings")) == 5
    await connection.run_sync(run, "upgrade")
    await db.rollback()  # Discard the isolated schema and all synthetic data.
