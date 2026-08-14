"""note lexical search vector

Revision ID: a5c9d3e7b2f4
Revises: f4b8c2e6a1d3
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a5c9d3e7b2f4"
down_revision = "f4b8c2e6a1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("search_vector", postgresql.TSVECTOR(),
        sa.Computed("to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content_markdown, ''))", persisted=True), nullable=True))
    op.create_index("ix_notes_search_vector", "notes", ["search_vector"], unique=False, postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_notes_search_vector", table_name="notes")
    op.drop_column("notes", "search_vector")
