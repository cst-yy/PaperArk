"""paper_reading_status

Revision ID: b8e5f1c4d2a7
Revises: a9d4e7b2c6f1
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e5f1c4d2a7"
down_revision: Union[str, None] = "a9d4e7b2c6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column(
            "reading_status",
            sa.String(length=20),
            server_default="unread",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_papers_reading_status",
        "papers",
        ["reading_status"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_papers_reading_status",
        "papers",
        "reading_status IN ('unread', 'reading', 'finished', 'archived')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_papers_reading_status", "papers", type_="check")
    op.drop_index("ix_papers_reading_status", table_name="papers")
    op.drop_column("papers", "reading_status")
