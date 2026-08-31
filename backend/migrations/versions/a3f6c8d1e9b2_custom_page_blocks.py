"""custom named page blocks

Revision ID: a3f6c8d1e9b2
Revises: b7d4e9a2c610
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f6c8d1e9b2"
down_revision: Union[str, None] = "b7d4e9a2c610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("page_blocks", sa.Column("name", sa.String(255), nullable=False, server_default="自动分区"))
    op.add_column("page_blocks", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_page_blocks_is_default", "page_blocks", ["is_default"], unique=False)
    op.create_index("ix_page_blocks_document_page_name", "page_blocks", ["document_id", "page_number", "name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_page_blocks_document_page_name", table_name="page_blocks")
    op.drop_index("ix_page_blocks_is_default", table_name="page_blocks")
    op.drop_column("page_blocks", "is_default")
    op.drop_column("page_blocks", "name")
