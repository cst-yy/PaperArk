"""add future work to research note profile

Revision ID: d8f1a6c3e9b2
Revises: c7e2f5a9b4d6
"""
from alembic import op
import sqlalchemy as sa

revision = "d8f1a6c3e9b2"
down_revision = "c7e2f5a9b4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_note_profiles",
        sa.Column("future_work", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("research_note_profiles", "future_work")
