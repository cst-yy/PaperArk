"""document_references

Revision ID: f6c2a9e7b4d1
Revises: e4b8c6a1f9d3
Create Date: 2026-08-14

Add PDF-derived Reference entries for S7-C. References are tied to their
Document; matching a library Paper is optional and survives Paper deletion.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6c2a9e7b4d1"
down_revision: Union[str, None] = "e4b8c6a1f9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("authors_json", sa.JSON(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("arxiv_id", sa.String(length=64), nullable=True),
        sa.Column("venue", sa.Text(), nullable=True),
        sa.Column("matched_paper_id", sa.Uuid(), nullable=True),
        sa.Column("match_method", sa.String(length=32), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_paper_id"], ["papers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "order_index", name="uq_references_document_order"),
    )
    op.create_index("ix_references_document_id", "references", ["document_id"])
    op.create_index("ix_references_section_id", "references", ["section_id"])
    op.create_index("ix_references_doi", "references", ["doi"])
    op.create_index("ix_references_arxiv_id", "references", ["arxiv_id"])
    op.create_index("ix_references_matched_paper_id", "references", ["matched_paper_id"])


def downgrade() -> None:
    op.drop_index("ix_references_matched_paper_id", table_name="references")
    op.drop_index("ix_references_arxiv_id", table_name="references")
    op.drop_index("ix_references_doi", table_name="references")
    op.drop_index("ix_references_section_id", table_name="references")
    op.drop_index("ix_references_document_id", table_name="references")
    op.drop_table("references")
