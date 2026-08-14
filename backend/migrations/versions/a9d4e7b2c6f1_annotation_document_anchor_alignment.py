"""annotation_document_anchor_alignment

Revision ID: a9d4e7b2c6f1
Revises: f2a6c9d1e5b3
Create Date: 2026-08-14

Align Annotation.document_id with the Evidence Anchor ORM contract.
The migration deliberately fails instead of guessing an anchor for historic rows.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9d4e7b2c6f1"
down_revision: Union[str, None] = "f2a6c9d1e5b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM annotations
                WHERE document_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce annotations.document_id NOT NULL: null rows exist';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM annotations AS annotation
                LEFT JOIN documents AS document ON document.id = annotation.document_id
                WHERE document.id IS NULL OR document.paper_id <> annotation.paper_id
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce annotations document anchor: invalid document/paper pairing exists';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint(
        "annotations_document_id_fkey",
        "annotations",
        type_="foreignkey",
    )
    op.alter_column("annotations", "document_id", nullable=False)
    op.create_foreign_key(
        "fk_annotations_document_id_documents",
        "annotations",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_annotations_document_id",
        "annotations",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_annotations_document_id", table_name="annotations")
    op.drop_constraint(
        "fk_annotations_document_id_documents",
        "annotations",
        type_="foreignkey",
    )
    op.alter_column("annotations", "document_id", nullable=True)
    op.create_foreign_key(
        "annotations_document_id_fkey",
        "annotations",
        "documents",
        ["document_id"],
        ondelete="SET NULL",
    )
