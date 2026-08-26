"""Add optimistic metadata revision to papers.

Revision ID: f7d4b1c8a2e6
Revises: e6c3a9f2b7d1
"""
from alembic import op
import sqlalchemy as sa

revision = "f7d4b1c8a2e6"
down_revision = "e6c3a9f2b7d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column("metadata_revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        "ck_papers_metadata_revision_positive", "papers", "metadata_revision >= 1"
    )


def downgrade() -> None:
    op.drop_constraint("ck_papers_metadata_revision_positive", "papers", type_="check")
    op.drop_column("papers", "metadata_revision")
