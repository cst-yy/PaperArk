"""AI analysis provenance and research profile revision

Revision ID: e9b4c2d7f1a6
Revises: d8f1a6c3e9b2
"""
from alembic import op
import sqlalchemy as sa

revision = "e9b4c2d7f1a6"
down_revision = "d8f1a6c3e9b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_note_profiles", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_type", sa.String(30), nullable=False, server_default="deep_reading"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ready"),
        sa.Column("provider_name", sa.String(100), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("retrieval_mode", sa.String(20), nullable=False),
        sa.Column("source_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("analysis_type IN ('deep_reading')", name="ck_ai_analysis_type"),
        sa.CheckConstraint("status IN ('ready')", name="ck_ai_analysis_status"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_user_id", "ai_analyses", ["user_id"])
    op.create_index("ix_ai_analyses_paper_id", "ai_analyses", ["paper_id"])
    op.create_index("ix_ai_analyses_source_snapshot_hash", "ai_analyses", ["source_snapshot_hash"])
    op.create_index("ix_ai_analyses_input_hash", "ai_analyses", ["input_hash"])
    op.create_table(
        "ai_analysis_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("section_title", sa.String(1000), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("retrieval_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "order_index", name="uq_ai_analysis_source_order"),
    )
    op.create_index("ix_ai_analysis_sources_analysis_id", "ai_analysis_sources", ["analysis_id"])
    op.create_index("ix_ai_analysis_sources_paper_id", "ai_analysis_sources", ["paper_id"])
    op.create_table(
        "ai_analysis_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("application_mode", sa.String(100), nullable=False),
        sa.Column("applied_fields_json", sa.JSON(), nullable=False),
        sa.Column("profile_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analysis_applications_analysis_id", "ai_analysis_applications", ["analysis_id"])
    op.create_index("ix_ai_analysis_applications_note_id", "ai_analysis_applications", ["note_id"])


def downgrade() -> None:
    op.drop_table("ai_analysis_applications")
    op.drop_table("ai_analysis_sources")
    op.drop_table("ai_analyses")
    op.drop_column("research_note_profiles", "revision")
