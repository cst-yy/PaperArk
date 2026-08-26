"""Track daily reading duration

Revision ID: d5b2f8a1c7e4
Revises: d1a7e4c9b2f6
"""
from alembic import op
import sqlalchemy as sa

revision = "d5b2f8a1c7e4"
down_revision = "d1a7e4c9b2f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reading_activities",
        sa.Column("reading_time_seconds", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("reading_activities", "reading_time_seconds")
