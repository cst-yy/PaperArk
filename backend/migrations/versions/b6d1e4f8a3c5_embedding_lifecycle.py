"""embedding lifecycle for chunks and notes

Revision ID: b6d1e4f8a3c5
Revises: a5c9d3e7b2f4
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "b6d1e4f8a3c5"
down_revision = "a5c9d3e7b2f4"
branch_labels = None
depends_on = None


def _lifecycle(table: str, add_vector: bool = False) -> None:
    if add_vector:
        op.add_column(table, sa.Column("embedding", Vector(384), nullable=True))
    op.add_column(table, sa.Column("embedding_model", sa.String(255), nullable=True))
    op.add_column(table, sa.Column("embedding_dimension", sa.Integer(), nullable=True))
    op.add_column(table, sa.Column("embedding_content_hash", sa.String(64), nullable=True))
    op.add_column(table, sa.Column("embedding_status", sa.String(20), server_default="pending", nullable=False))
    op.add_column(table, sa.Column("embedding_error", sa.Text(), nullable=True))
    op.create_check_constraint(f"ck_{table}_embedding_status", table, "embedding_status IN ('pending', 'processing', 'ready', 'failed')")
    op.create_index(f"ix_{table}_embedding_status", table, ["embedding_status"])


def upgrade() -> None:
    _lifecycle("chunks")
    _lifecycle("notes", add_vector=True)


def downgrade() -> None:
    for table in ("notes", "chunks"):
        op.drop_index(f"ix_{table}_embedding_status", table_name=table)
        op.drop_constraint(f"ck_{table}_embedding_status", table_name=table, type_="check")
        for column in ("embedding_error", "embedding_status", "embedding_content_hash", "embedding_dimension", "embedding_model"):
            op.drop_column(table, column)
    op.drop_column("notes", "embedding")
