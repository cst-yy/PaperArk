"""semantic HNSW indexes

Revision ID: c7e2f5a9b4d6
Revises: b6d1e4f8a3c5
"""
from alembic import op

revision = "c7e2f5a9b4d6"
down_revision = "b6d1e4f8a3c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL")
    op.execute("CREATE INDEX ix_notes_embedding_hnsw ON notes USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL")


def downgrade() -> None:
    op.drop_index("ix_notes_embedding_hnsw", table_name="notes")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
