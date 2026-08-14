"""tag_normalized_name

Revision ID: d4b7e8f2a9c1
Revises: a6e9d2c4b7f0
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b7e8f2a9c1"
down_revision: Union[str, None] = "a6e9d2c4b7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tags", sa.Column("normalized_name", sa.String(length=100), nullable=True))
    op.execute("UPDATE tags SET normalized_name = lower(btrim(name))")
    duplicates = op.get_bind().execute(
        sa.text(
            "SELECT user_id, normalized_name FROM tags "
            "GROUP BY user_id, normalized_name HAVING count(*) > 1"
        )
    ).all()
    if duplicates:
        raise RuntimeError("Existing duplicate normalized tag names must be resolved before migration")
    op.alter_column("tags", "normalized_name", nullable=False)
    op.create_unique_constraint("uq_tag_user_normalized_name", "tags", ["user_id", "normalized_name"])


def downgrade() -> None:
    op.drop_constraint("uq_tag_user_normalized_name", "tags", type_="unique")
    op.drop_column("tags", "normalized_name")
