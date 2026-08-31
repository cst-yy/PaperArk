"""paper author roles and research identity

Revision ID: 9c2e7a4b6d10
Revises: 44ef08614b89
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9c2e7a4b6d10"
down_revision: Union[str, None] = "44ef08614b89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("paper_authors", sa.Column("is_co_first", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("paper_authors", sa.Column("is_corresponding", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "research_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_research_identity_user"),
    )
    op.create_index("ix_research_identities_user_id", "research_identities", ["user_id"])
    op.create_index("ix_research_identities_author_id", "research_identities", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_research_identities_author_id", table_name="research_identities")
    op.drop_index("ix_research_identities_user_id", table_name="research_identities")
    op.drop_table("research_identities")
    op.drop_column("paper_authors", "is_corresponding")
    op.drop_column("paper_authors", "is_co_first")
