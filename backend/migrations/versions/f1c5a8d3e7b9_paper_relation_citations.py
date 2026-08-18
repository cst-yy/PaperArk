"""Paper relation citation provenance

Revision ID: f1c5a8d3e7b9
Revises: e9b4c2d7f1a6
"""
from alembic import op
import sqlalchemy as sa

revision = "f1c5a8d3e7b9"
down_revision = "e9b4c2d7f1a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The pre-S12 placeholder had no ownership or provenance contract. Remove
    # unsupported placeholder rows before tightening it to the first formal type.
    op.execute("DELETE FROM paper_relations WHERE relation_type <> 'cites'")
    op.add_column("paper_relations", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("paper_relations", sa.Column("origin", sa.String(20), nullable=False, server_default="reference"))
    op.add_column("paper_relations", sa.Column("source_reference_id", sa.Uuid(), nullable=True))
    op.alter_column("paper_relations", "score", new_column_name="confidence")
    op.execute("""
        UPDATE paper_relations AS relation
        SET user_id = paper.user_id
        FROM papers AS paper
        WHERE paper.id = relation.source_paper_id
    """)
    op.alter_column("paper_relations", "user_id", nullable=False)
    op.drop_constraint("uq_paper_relation", "paper_relations", type_="unique")
    op.create_unique_constraint(
        "uq_paper_relation", "paper_relations",
        ["user_id", "source_paper_id", "target_paper_id", "relation_type"],
    )
    op.create_foreign_key("fk_paper_relations_user", "paper_relations", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_paper_relations_reference", "paper_relations", "references", ["source_reference_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_paper_relation_type", "paper_relations", "relation_type IN ('cites')")
    op.create_check_constraint("ck_paper_relation_origin", "paper_relations", "origin IN ('reference', 'manual', 'ai')")
    op.create_check_constraint("ck_paper_relation_not_self", "paper_relations", "source_paper_id <> target_paper_id")
    op.create_index("ix_paper_relations_user_id", "paper_relations", ["user_id"])
    op.create_index("ix_paper_relations_source_reference_id", "paper_relations", ["source_reference_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_relations_source_reference_id", table_name="paper_relations")
    op.drop_index("ix_paper_relations_user_id", table_name="paper_relations")
    op.drop_constraint("ck_paper_relation_not_self", "paper_relations", type_="check")
    op.drop_constraint("ck_paper_relation_origin", "paper_relations", type_="check")
    op.drop_constraint("ck_paper_relation_type", "paper_relations", type_="check")
    op.drop_constraint("fk_paper_relations_reference", "paper_relations", type_="foreignkey")
    op.drop_constraint("fk_paper_relations_user", "paper_relations", type_="foreignkey")
    op.drop_constraint("uq_paper_relation", "paper_relations", type_="unique")
    op.create_unique_constraint("uq_paper_relation", "paper_relations", ["source_paper_id", "target_paper_id", "relation_type"])
    op.alter_column("paper_relations", "confidence", new_column_name="score")
    op.drop_column("paper_relations", "source_reference_id")
    op.drop_column("paper_relations", "origin")
    op.drop_column("paper_relations", "user_id")
