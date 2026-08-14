"""research note profile

Revision ID: f4b8c2e6a1d3
Revises: e3a7b1d5f9c2
Create Date: 2026-08-14
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
revision: str = "f4b8c2e6a1d3"
down_revision: Union[str, None] = "e3a7b1d5f9c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("research_note_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("note_id", sa.Uuid(), nullable=False),
        *[sa.Column(name, sa.Text(), server_default="", nullable=False) for name in ("background","prior_work_limitations","research_problem","method_summary","results_summary","conclusion","limitations","my_thoughts")],
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"), sa.UniqueConstraint("note_id"))
    op.create_index("ix_research_note_profiles_note_id", "research_note_profiles", ["note_id"], unique=True)
    op.create_table("research_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("research_note_id", sa.Uuid(), nullable=False), sa.Column("order_index", sa.Integer(), nullable=False),
        *[sa.Column(name, sa.Text(), server_default="", nullable=False) for name in ("problem","prior_limitation","innovation","solution")],
        sa.Column("evidence_summary", sa.Text(), nullable=True), sa.ForeignKeyConstraint(["research_note_id"], ["research_note_profiles.id"], ondelete="CASCADE"), sa.UniqueConstraint("research_note_id","order_index",name="uq_research_contribution_order"))
    op.create_index("ix_research_contributions_research_note_id", "research_contributions", ["research_note_id"])
    op.create_table("research_experiments",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("research_note_id", sa.Uuid(), nullable=False), sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("task", sa.Text(), server_default="", nullable=False), sa.Column("datasets_json", sa.JSON(), nullable=False), sa.Column("baselines_json", sa.JSON(), nullable=False), sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("result", sa.Text(), server_default="", nullable=False), sa.Column("conclusion", sa.Text(), server_default="", nullable=False),
        sa.ForeignKeyConstraint(["research_note_id"], ["research_note_profiles.id"], ondelete="CASCADE"), sa.UniqueConstraint("research_note_id","order_index",name="uq_research_experiment_order"))
    op.create_index("ix_research_experiments_research_note_id", "research_experiments", ["research_note_id"])
    op.create_table("contribution_evidence", sa.Column("contribution_id",sa.Uuid(),primary_key=True),sa.Column("note_evidence_id",sa.Uuid(),primary_key=True),sa.ForeignKeyConstraint(["contribution_id"],["research_contributions.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["note_evidence_id"],["note_evidence.id"],ondelete="CASCADE"))
    op.create_table("experiment_evidence", sa.Column("experiment_id",sa.Uuid(),primary_key=True),sa.Column("note_evidence_id",sa.Uuid(),primary_key=True),sa.ForeignKeyConstraint(["experiment_id"],["research_experiments.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["note_evidence_id"],["note_evidence.id"],ondelete="CASCADE"))
    op.create_table("experiment_contributions", sa.Column("experiment_id",sa.Uuid(),primary_key=True),sa.Column("contribution_id",sa.Uuid(),primary_key=True),sa.ForeignKeyConstraint(["experiment_id"],["research_experiments.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["contribution_id"],["research_contributions.id"],ondelete="CASCADE"))

def downgrade() -> None:
    for table in ("experiment_contributions","experiment_evidence","contribution_evidence"): op.drop_table(table)
    op.drop_index("ix_research_experiments_research_note_id", table_name="research_experiments"); op.drop_table("research_experiments")
    op.drop_index("ix_research_contributions_research_note_id", table_name="research_contributions"); op.drop_table("research_contributions")
    op.drop_index("ix_research_note_profiles_note_id", table_name="research_note_profiles"); op.drop_table("research_note_profiles")
