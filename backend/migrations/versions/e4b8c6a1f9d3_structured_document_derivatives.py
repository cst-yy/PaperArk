"""structured_document_derivatives

Revision ID: e4b8c6a1f9d3
Revises: d3f7a2e9c5b4
Create Date: 2026-08-14

Evolve the existing Section/Chunk tables for S7-B without introducing v2 tables.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4b8c6a1f9d3"
down_revision: Union[str, None] = "d3f7a2e9c5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sections", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("sections", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("page_end", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("char_count", sa.Integer(), nullable=True))
    op.execute("UPDATE chunks SET page_start = page_number, page_end = page_number WHERE page_number IS NOT NULL")
    op.execute("DELETE FROM chunks WHERE content IS NULL OR btrim(content) = ''")
    op.execute(
        """
        DELETE FROM chunks AS duplicate
        USING chunks AS retained
        WHERE duplicate.document_id = retained.document_id
          AND duplicate.chunk_index = retained.chunk_index
          AND duplicate.id > retained.id
        """
    )
    op.create_unique_constraint("uq_chunks_document_order", "chunks", ["document_id", "chunk_index"])


def downgrade() -> None:
    op.drop_constraint("uq_chunks_document_order", "chunks", type_="unique")
    op.drop_column("chunks", "char_count")
    op.drop_column("chunks", "page_end")
    op.drop_column("chunks", "page_start")
    op.drop_column("sections", "updated_at")
    op.drop_column("sections", "created_at")
