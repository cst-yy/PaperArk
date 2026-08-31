"""Add user-authored mind map nodes and edges.

Revision ID: c5f8a3d1e7b9
Revises: b4e7d2c9a1f5
"""
from alembic import op
import sqlalchemy as sa

revision = "c5f8a3d1e7b9"
down_revision = "b4e7d2c9a1f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("manual_mind_map_nodes", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("summary", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_manual_mind_map_nodes_user_id", "manual_mind_map_nodes", ["user_id"])
    op.create_index("ix_manual_mind_map_nodes_paper_id", "manual_mind_map_nodes", ["paper_id"])
    op.create_table("manual_mind_map_edges", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False), sa.Column("source_key", sa.String(200), nullable=False), sa.Column("target_key", sa.String(200), nullable=False), sa.Column("relation", sa.String(100), nullable=False, server_default="关联"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_manual_mind_map_edges_user_id", "manual_mind_map_edges", ["user_id"])
    op.create_index("ix_manual_mind_map_edges_paper_id", "manual_mind_map_edges", ["paper_id"])
    op.create_index("ix_manual_mind_map_edges_source_key", "manual_mind_map_edges", ["source_key"])
    op.create_index("ix_manual_mind_map_edges_target_key", "manual_mind_map_edges", ["target_key"])


def downgrade() -> None:
    op.drop_table("manual_mind_map_edges")
    op.drop_table("manual_mind_map_nodes")
