"""annotation_evidence_layer

Revision ID: f15c0b6d7e91
Revises: c0491cb1a8b2
Create Date: 2026-08-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f15c0b6d7e91"
down_revision: Union[str, None] = "c0491cb1a8b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("annotations", sa.Column("comment", sa.Text(), nullable=True))
    op.add_column("annotations", sa.Column("prefix_text", sa.Text(), nullable=True))
    op.add_column("annotations", sa.Column("suffix_text", sa.Text(), nullable=True))
    op.add_column("annotations", sa.Column("position_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(
        "ix_annotations_user_paper_page",
        "annotations",
        ["user_id", "paper_id", "page_number"],
        unique=False,
    )
    # Existing imported annotations have no reliable Document anchor. New S5
    # records are enforced at the application layer while historic rows remain readable.


def downgrade() -> None:
    op.drop_index("ix_annotations_user_paper_page", table_name="annotations")
    op.drop_column("annotations", "position_data")
    op.drop_column("annotations", "suffix_text")
    op.drop_column("annotations", "prefix_text")
    op.drop_column("annotations", "comment")
