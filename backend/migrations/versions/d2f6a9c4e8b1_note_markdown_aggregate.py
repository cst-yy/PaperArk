"""note markdown aggregate

Revision ID: d2f6a9c4e8b1
Revises: c9d4e7f2a1b8
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2f6a9c4e8b1"
down_revision: Union[str, None] = "c9d4e7f2a1b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("notes", "paper_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("notes", "content", new_column_name="content_markdown", existing_type=sa.Text())
    op.execute("UPDATE notes SET title = 'Untitled note' WHERE title IS NULL OR btrim(title) = ''")
    op.alter_column("notes", "title", existing_type=sa.String(500), nullable=False, server_default="Untitled note")
    op.alter_column("notes", "content_markdown", existing_type=sa.Text(), nullable=False, server_default="")
    op.add_column("notes", sa.Column("note_type", sa.String(20), server_default="general", nullable=False))
    op.create_index("ix_notes_note_type", "notes", ["note_type"])
    op.create_check_constraint("ck_notes_note_type", "notes", "note_type IN ('general', 'paper', 'research')")
    op.execute("UPDATE notes SET note_type = CASE WHEN paper_id IS NULL THEN 'general' ELSE 'paper' END")


def downgrade() -> None:
    op.drop_constraint("ck_notes_note_type", "notes", type_="check")
    op.drop_index("ix_notes_note_type", table_name="notes")
    op.drop_column("notes", "note_type")
    op.alter_column("notes", "content_markdown", new_column_name="content", existing_type=sa.Text(), server_default=None)
    op.alter_column("notes", "title", existing_type=sa.String(500), nullable=True, server_default=None)
    op.execute("DELETE FROM notes WHERE paper_id IS NULL")
    op.alter_column("notes", "paper_id", existing_type=sa.Uuid(), nullable=False)
