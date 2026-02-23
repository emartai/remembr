"""Add embeddings table with pgvector

Revision ID: 002
Revises: 001
Create Date: 2026-02-23 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('episode_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('memory_fact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('vector', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['memory_fact_id'], ['memory_facts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_embeddings_org_id'), 'embeddings', ['org_id'], unique=False)
    op.create_index(op.f('ix_embeddings_episode_id'), 'embeddings', ['episode_id'], unique=False)
    op.create_index(op.f('ix_embeddings_memory_fact_id'), 'embeddings', ['memory_fact_id'], unique=False)
    op.create_index(op.f('ix_embeddings_model'), 'embeddings', ['model'], unique=False)

    # Create HNSW index for fast approximate nearest neighbor search
    # Using cosine distance operator (<=>)
    op.execute(
        'CREATE INDEX ix_embeddings_vector_cosine ON embeddings '
        'USING hnsw (vector vector_cosine_ops)'
    )


def downgrade() -> None:
    op.drop_index('ix_embeddings_vector_cosine', table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_model'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_memory_fact_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_episode_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_org_id'), table_name='embeddings')
    op.drop_table('embeddings')
    # Note: We don't drop the vector extension as other tables might use it
