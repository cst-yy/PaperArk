"""keyword_taxonomy

Revision ID: e7c3f1a8b4d2
Revises: d4b7e8f2a9c1
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c3f1a8b4d2"
down_revision: Union[str, None] = "d4b7e8f2a9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "keywords",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("normalized_name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_keyword_user_normalized_name"),
    )
    op.create_index(op.f("ix_keywords_user_id"), "keywords", ["user_id"], unique=False)
    op.create_table(
        "paper_keywords",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paper_id", "keyword_id", "source", name="uq_paper_keyword_source"),
    )
    op.create_index(op.f("ix_paper_keywords_paper_id"), "paper_keywords", ["paper_id"], unique=False)
    op.create_index(op.f("ix_paper_keywords_keyword_id"), "paper_keywords", ["keyword_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_paper_keywords_keyword_id"), table_name="paper_keywords")
    op.drop_index(op.f("ix_paper_keywords_paper_id"), table_name="paper_keywords")
    op.drop_table("paper_keywords")
    op.drop_index(op.f("ix_keywords_user_id"), table_name="keywords")
    op.drop_table("keywords")
