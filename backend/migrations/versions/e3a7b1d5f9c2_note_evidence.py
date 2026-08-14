"""note evidence

Revision ID: e3a7b1d5f9c2
Revises: d2f6a9c4e8b1
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3a7b1d5f9c2"
down_revision: Union[str, None] = "d2f6a9c4e8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("annotation_id", sa.Uuid(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("quote_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["annotation_id"], ["annotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "annotation_id", name="uq_note_evidence_annotation"),
        sa.UniqueConstraint("note_id", "order_index", name="uq_note_evidence_order"),
    )
    op.create_index("ix_note_evidence_note_id", "note_evidence", ["note_id"])
    op.create_index("ix_note_evidence_annotation_id", "note_evidence", ["annotation_id"])


def downgrade() -> None:
    op.drop_index("ix_note_evidence_annotation_id", table_name="note_evidence")
    op.drop_index("ix_note_evidence_note_id", table_name="note_evidence")
    op.drop_table("note_evidence")
