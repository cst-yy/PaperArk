"""document_elements

Revision ID: a7d3f9c2e5b6
Revises: f6c2a9e7b4d1
Create Date: 2026-08-14

Add caption-derived PDF figure/table metadata for S7-D.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d3f9c2e5b6"
down_revision: Union[str, None] = "f6c2a9e7b4d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_elements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("element_type", sa.String(length=16), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=16), server_default="pdf", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("element_type IN ('figure', 'table')", name="ck_document_elements_type"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "order_index", name="uq_document_elements_order"),
    )
    op.create_index("ix_document_elements_document_id", "document_elements", ["document_id"])
    op.create_index("ix_document_elements_section_id", "document_elements", ["section_id"])
    op.create_index("ix_document_elements_element_type", "document_elements", ["element_type"])


def downgrade() -> None:
    op.drop_index("ix_document_elements_element_type", table_name="document_elements")
    op.drop_index("ix_document_elements_section_id", table_name="document_elements")
    op.drop_index("ix_document_elements_document_id", table_name="document_elements")
    op.drop_table("document_elements")
