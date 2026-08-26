"""Add Paper List metadata fields

Revision ID: e6c3a9f2b7d1
Revises: d5b2f8a1c7e4
"""
from alembic import op
import sqlalchemy as sa

revision = "e6c3a9f2b7d1"
down_revision = "d5b2f8a1c7e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("title_zh", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("citation_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("papers", "citation_text")
    op.drop_column("papers", "title_zh")
