"""document_file_hash

Revision ID: a6e9d2c4b7f0
Revises: f15c0b6d7e91
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6e9d2c4b7f0"
down_revision: Union[str, None] = "f15c0b6d7e91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_column("documents", "file_hash")
