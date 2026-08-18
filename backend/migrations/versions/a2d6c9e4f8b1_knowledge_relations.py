"""Knowledge relations, evidence, and suggestions

Revision ID: a2d6c9e4f8b1
Revises: f1c5a8d3e7b9
"""
from alembic import op
import sqlalchemy as sa

revision = "a2d6c9e4f8b1"
down_revision = "f1c5a8d3e7b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_paper_relation_type", "paper_relations", type_="check")
    op.create_check_constraint("ck_paper_relation_type", "paper_relations", "relation_type IN ('cites','extends','improves','contrasts','supports','uses','similar')")
    op.add_column("paper_relations", sa.Column("note", sa.Text(), nullable=True))
    op.create_table("paper_relation_evidence",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("relation_id", sa.Uuid(), nullable=False),
        sa.Column("annotation_id", sa.Uuid(), nullable=True), sa.Column("source_reference_id", sa.Uuid(), nullable=True),
        sa.Column("quote_snapshot", sa.Text(), nullable=False), sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("(annotation_id IS NOT NULL AND source_reference_id IS NULL) OR (annotation_id IS NULL AND source_reference_id IS NOT NULL)", name="ck_paper_relation_evidence_exactly_one_source"),
        sa.ForeignKeyConstraint(["relation_id"], ["paper_relations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["annotation_id"], ["annotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_reference_id"], ["references.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("relation_id", "order_index", name="uq_paper_relation_evidence_order"))
    for column in ("relation_id", "annotation_id", "source_reference_id"):
        op.create_index(f"ix_paper_relation_evidence_{column}", "paper_relation_evidence", [column])
    op.create_table("paper_relation_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_paper_id", sa.Uuid(), nullable=False), sa.Column("target_paper_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(30), nullable=False), sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("provider_name", sa.String(100), nullable=False), sa.Column("model", sa.String(255), nullable=False),
        sa.Column("accepted_relation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("relation_type IN ('extends','improves','contrasts','supports','uses','similar')", name="ck_relation_suggestion_type"),
        sa.CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_relation_suggestion_status"),
        sa.CheckConstraint("source_paper_id <> target_paper_id", name="ck_relation_suggestion_not_self"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_relation_id"], ["paper_relations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"))
    for column in ("user_id", "source_paper_id", "target_paper_id", "status"):
        op.create_index(f"ix_paper_relation_suggestions_{column}", "paper_relation_suggestions", [column])


def downgrade() -> None:
    op.drop_table("paper_relation_suggestions")
    op.drop_table("paper_relation_evidence")
    op.drop_column("paper_relations", "note")
    op.drop_constraint("ck_paper_relation_type", "paper_relations", type_="check")
    op.create_check_constraint("ck_paper_relation_type", "paper_relations", "relation_type IN ('cites')")
