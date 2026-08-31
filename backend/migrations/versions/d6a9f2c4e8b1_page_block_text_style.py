"""Persist page-block translation text style.

Revision ID: d6a9f2c4e8b1
Revises: c5f8a3d1e7b9
"""

from alembic import op
import sqlalchemy as sa


revision = "d6a9f2c4e8b1"
down_revision = "c5f8a3d1e7b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "page_blocks",
        sa.Column(
            "text_style",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{\"font_size\": 12, \"color\": \"#1f2937\"}'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("page_blocks", "text_style")
