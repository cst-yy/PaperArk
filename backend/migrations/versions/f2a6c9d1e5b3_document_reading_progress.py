"""document_reading_progress

Revision ID: f2a6c9d1e5b3
Revises: e7c3f1a8b4d2
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a6c9d1e5b3"
down_revision: Union[str, None] = "e7c3f1a8b4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reading_progress", sa.Column("document_id", sa.Uuid(), nullable=True))
    op.add_column("reading_progress", sa.Column("total_pages", sa.Integer(), nullable=True))
    op.add_column("reading_progress", sa.Column("progress_ratio", sa.Float(), nullable=True))
    op.add_column("reading_progress", sa.Column("reading_time_seconds", sa.Integer(), nullable=True))

    # Historic rows were paper-scoped. Map each row to the newest document for
    # the same paper, then remove rows whose paper has no document to own it.
    op.execute("""
        UPDATE reading_progress AS progress
        SET document_id = source.document_id
        FROM (
            SELECT DISTINCT ON (paper_id) paper_id, id AS document_id
            FROM documents
            ORDER BY paper_id, created_at DESC, id DESC
        ) AS source
        WHERE progress.paper_id = source.paper_id
    """)
    op.execute("DELETE FROM reading_progress WHERE document_id IS NULL")
    op.execute("""
        UPDATE reading_progress
        SET total_pages = GREATEST(current_page, 1),
            progress_ratio = CASE
                WHEN current_page > 0 THEN 1.0
                ELSE 0.0
            END,
            reading_time_seconds = total_read_time
    """)
    # The legacy table had no uniqueness guarantee. Retain the most recently
    # read row if historic duplicates resolve to the same concrete document.
    op.execute("""
        DELETE FROM reading_progress
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, document_id
                    ORDER BY last_read_at DESC, id DESC
                ) AS row_number
                FROM reading_progress
            ) AS ranked
            WHERE ranked.row_number > 1
        )
    """)

    op.drop_index(op.f("ix_reading_progress_paper_id"), table_name="reading_progress")
    op.drop_constraint("reading_progress_paper_id_fkey", "reading_progress", type_="foreignkey")
    op.drop_column("reading_progress", "paper_id")
    op.drop_column("reading_progress", "scroll_position")
    op.drop_column("reading_progress", "progress_percent")
    op.drop_column("reading_progress", "total_read_time")

    op.alter_column("reading_progress", "document_id", nullable=False)
    op.alter_column("reading_progress", "total_pages", nullable=False)
    op.alter_column("reading_progress", "progress_ratio", nullable=False)
    op.alter_column("reading_progress", "reading_time_seconds", nullable=False)
    op.create_foreign_key(
        "fk_reading_progress_document_id_documents",
        "reading_progress",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_reading_progress_document_id"), "reading_progress", ["document_id"], unique=False)
    op.create_unique_constraint(
        "uq_reading_progress_user_document",
        "reading_progress",
        ["user_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_reading_progress_user_document", "reading_progress", type_="unique")
    op.drop_index(op.f("ix_reading_progress_document_id"), table_name="reading_progress")
    op.drop_constraint("fk_reading_progress_document_id_documents", "reading_progress", type_="foreignkey")
    op.add_column("reading_progress", sa.Column("paper_id", sa.Uuid(), nullable=True))
    op.add_column("reading_progress", sa.Column("scroll_position", sa.Float(), nullable=True))
    op.add_column("reading_progress", sa.Column("progress_percent", sa.Float(), nullable=True))
    op.add_column("reading_progress", sa.Column("total_read_time", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE reading_progress AS progress
        SET paper_id = documents.paper_id,
            scroll_position = 0.0,
            progress_percent = progress.progress_ratio * 100,
            total_read_time = progress.reading_time_seconds
        FROM documents
        WHERE documents.id = progress.document_id
    """)
    op.alter_column("reading_progress", "paper_id", nullable=False)
    op.alter_column("reading_progress", "scroll_position", nullable=False)
    op.alter_column("reading_progress", "progress_percent", nullable=False)
    op.alter_column("reading_progress", "total_read_time", nullable=False)
    op.create_foreign_key(
        "reading_progress_paper_id_fkey",
        "reading_progress",
        "papers",
        ["paper_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_reading_progress_paper_id"), "reading_progress", ["paper_id"], unique=False)
    op.drop_column("reading_progress", "reading_time_seconds")
    op.drop_column("reading_progress", "progress_ratio")
    op.drop_column("reading_progress", "total_pages")
    op.drop_column("reading_progress", "document_id")
