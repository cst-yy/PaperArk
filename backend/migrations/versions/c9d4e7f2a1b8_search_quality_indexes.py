"""search quality indexes

Revision ID: c9d4e7f2a1b8
Revises: a7d3f9c2e5b6
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c9d4e7f2a1b8"
down_revision: Union[str, None] = "a7d3f9c2e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table, column in (
        ("papers", "title"), ("papers", "journal"), ("papers", "conference"),
        ("papers", "publisher"), ("authors", "name"), ("tags", "name"),
        ("keywords", "display_name"),
    ):
        op.execute(
            f'CREATE INDEX ix_{table}_{column}_trgm ON {table} '
            f'USING gin ({column} gin_trgm_ops)'
        )
    for table, expression in (
        ("chunks", "content"),
        ("sections", "coalesce(title, '') || ' ' || coalesce(content, '')"),
        ("references", "coalesce(title, '') || ' ' || coalesce(raw_text, '')"),
        ("document_elements", "coalesce(label, '') || ' ' || coalesce(caption, '')"),
    ):
        quoted_table = f'"{table}"' if table == "references" else table
        op.execute(
            f"ALTER TABLE {quoted_table} ADD COLUMN search_vector tsvector "
            f"GENERATED ALWAYS AS (to_tsvector('simple', {expression})) STORED"
        )
        op.execute(f"CREATE INDEX ix_{table}_search_vector ON {quoted_table} USING gin (search_vector)")


def downgrade() -> None:
    for table in ("document_elements", "references", "sections", "chunks"):
        quoted_table = f'"{table}"' if table == "references" else table
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_search_vector")
        op.execute(f"ALTER TABLE {quoted_table} DROP COLUMN search_vector")
    for table, column in (
        ("keywords", "display_name"), ("tags", "name"), ("authors", "name"),
        ("papers", "publisher"), ("papers", "conference"), ("papers", "journal"),
        ("papers", "title"),
    ):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{column}_trgm")
