"""document_parser_lifecycle

Revision ID: d3f7a2e9c5b4
Revises: b8e5f1c4d2a7
Create Date: 2026-08-14

Unifies historical Document parse states with the S7-A lifecycle and records the
parser implementation that generated successful metadata.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3f7a2e9c5b4"
down_revision: Union[str, None] = "b8e5f1c4d2a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "documents",
        "parse_status",
        existing_type=sa.String(length=20),
        server_default="pending",
        existing_nullable=False,
    )
    op.execute(
        "UPDATE documents SET parse_status = 'processing' WHERE parse_status = 'parsing'"
    )
    op.execute(
        "UPDATE documents SET parse_status = 'ready' WHERE parse_status = 'parsed'"
    )
    op.execute(
        "UPDATE documents SET parse_status = 'pending' "
        "WHERE parse_status IS NULL OR parse_status NOT IN ('pending', 'processing', 'ready', 'failed')"
    )
    op.add_column(
        "documents",
        sa.Column("parser_version", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_documents_parse_status", "documents", ["parse_status"], unique=False
    )
    op.create_check_constraint(
        "ck_documents_parse_status",
        "documents",
        "parse_status IN ('pending', 'processing', 'ready', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_parse_status", "documents", type_="check")
    op.drop_index("ix_documents_parse_status", table_name="documents")
    op.drop_column("documents", "parser_version")
    op.execute("UPDATE documents SET parse_status = 'parsing' WHERE parse_status = 'processing'")
    op.execute("UPDATE documents SET parse_status = 'parsed' WHERE parse_status = 'ready'")
