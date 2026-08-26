"""Dashboard todos, memos, and folder optimistic revision.

Revision ID: a1c5e8f3b7d9
Revises: f7d4b1c8a2e6
"""
from alembic import op
import sqlalchemy as sa

revision = "a1c5e8f3b7d9"
down_revision = "f7d4b1c8a2e6"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("folders", sa.Column("revision", sa.Integer(), server_default="1", nullable=False))
    op.create_check_constraint("ck_folders_revision_positive", "folders", "revision >= 1")
    op.create_table("todos",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("completed", sa.Boolean(), server_default="false", nullable=False), sa.Column("priority", sa.String(16), server_default="normal", nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=True), sa.Column("related_paper_id", sa.Uuid(), nullable=True), sa.Column("position", sa.Integer(), server_default="0", nullable=False), sa.Column("revision", sa.Integer(), server_default="1", nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high')", name="ck_todos_priority"), sa.CheckConstraint("revision >= 1", name="ck_todos_revision_positive"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["related_paper_id"], ["papers.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_todos_user_id", "todos", ["user_id"]); op.create_index("ix_todos_related_paper_id", "todos", ["related_paper_id"]); op.create_index("ix_todos_user_completed_due", "todos", ["user_id", "completed", "due_at"]); op.create_index("ix_todos_user_position", "todos", ["user_id", "position"])
    op.create_table("memos",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("color", sa.String(20), nullable=True), sa.Column("pinned", sa.Boolean(), server_default="false", nullable=False), sa.Column("related_paper_id", sa.Uuid(), nullable=True), sa.Column("revision", sa.Integer(), server_default="1", nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_memos_revision_positive"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["related_paper_id"], ["papers.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_memos_user_id", "memos", ["user_id"]); op.create_index("ix_memos_related_paper_id", "memos", ["related_paper_id"]); op.create_index("ix_memos_user_pinned_updated", "memos", ["user_id", "pinned", "updated_at"])

def downgrade() -> None:
    op.drop_table("memos"); op.drop_table("todos")
    op.drop_constraint("ck_folders_revision_positive", "folders", type_="check"); op.drop_column("folders", "revision")
