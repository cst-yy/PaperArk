"""Add daily document reading activity

Revision ID: d1a7e4c9b2f6
Revises: c4e8a1d7b3f9
"""
from alembic import op
import sqlalchemy as sa

revision = "d1a7e4c9b2f6"
down_revision = "c4e8a1d7b3f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("first_read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "document_id", "activity_date", name="uq_reading_activity_user_document_date"),
    )
    op.create_index("ix_reading_activities_user_id", "reading_activities", ["user_id"])
    op.create_index("ix_reading_activities_paper_id", "reading_activities", ["paper_id"])
    op.create_index("ix_reading_activities_document_id", "reading_activities", ["document_id"])
    op.create_index("ix_reading_activities_activity_date", "reading_activities", ["activity_date"])


def downgrade() -> None:
    op.drop_table("reading_activities")
