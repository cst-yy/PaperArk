"""Persist graph node positions separately from knowledge data

Revision ID: c4e8a1d7b3f9
Revises: a2d6c9e4f8b1
"""
from alembic import op
import sqlalchemy as sa

revision = "c4e8a1d7b3f9"
down_revision = "a2d6c9e4f8b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("graph_layouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("graph_type", sa.String(20), nullable=False),
        sa.Column("scope_key", sa.String(500), nullable=False),
        sa.Column("layout_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("graph_type IN ('citation','knowledge','mind_map')", name="ck_graph_layout_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "graph_type", "scope_key", name="uq_graph_layout_scope"))
    op.create_index("ix_graph_layouts_user_id", "graph_layouts", ["user_id"])
    op.create_index("ix_graph_layouts_graph_type", "graph_layouts", ["graph_type"])


def downgrade() -> None:
    op.drop_table("graph_layouts")
