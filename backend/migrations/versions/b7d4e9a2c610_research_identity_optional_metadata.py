"""research identity optional metadata

Revision ID: b7d4e9a2c610
Revises: 9c2e7a4b6d10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b7d4e9a2c610"
down_revision: Union[str, None] = "9c2e7a4b6d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("research_identities", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("research_identities", sa.Column("orcid", sa.String(50), nullable=True))
    op.add_column("research_identities", sa.Column("email", sa.String(255), nullable=True))
    op.execute("""UPDATE research_identities ri SET display_name = a.name, orcid = a.orcid FROM authors a WHERE a.id = ri.author_id""")
    op.alter_column("research_identities", "display_name", nullable=False)


def downgrade() -> None:
    op.drop_column("research_identities", "email")
    op.drop_column("research_identities", "orcid")
    op.drop_column("research_identities", "display_name")
