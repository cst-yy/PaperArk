"""Persist annotation underline styles.

Revision ID: b4e7d2c9a1f5
Revises: a3f6c8d1e9b2
"""
from alembic import op
import sqlalchemy as sa

revision = "b4e7d2c9a1f5"
down_revision = "a3f6c8d1e9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("annotations", sa.Column("line_style", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("annotations", "line_style")
