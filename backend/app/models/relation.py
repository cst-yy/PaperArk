import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaperRelation(Base):
    """Relationships between papers: cites, cited_by, related, extends, etc."""

    __tablename__ = "paper_relations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_paper_id",
            "target_paper_id",
            "relation_type",
            name="uq_paper_relation",
        ),
        CheckConstraint("relation_type IN ('cites','extends','improves','contrasts','supports','uses','similar')", name="ck_paper_relation_type"),
        CheckConstraint("origin IN ('reference', 'manual', 'ai')", name="ck_paper_relation_origin"),
        CheckConstraint("source_paper_id <> target_paper_id", name="ck_paper_relation_not_self"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    target_paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    relation_type: Mapped[str] = mapped_column(String(50))
    origin: Mapped[str] = mapped_column(String(20), default="reference", server_default="reference")
    source_reference_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("references.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_paper: Mapped["Paper"] = relationship(
        "Paper",
        back_populates="outgoing_relations",
        foreign_keys=[source_paper_id],
    )
    target_paper: Mapped["Paper"] = relationship(
        "Paper",
        back_populates="incoming_relations",
        foreign_keys=[target_paper_id],
    )


class PaperRelationEvidence(Base):
    __tablename__ = "paper_relation_evidence"
    __table_args__ = (
        UniqueConstraint("relation_id", "order_index", name="uq_paper_relation_evidence_order"),
        CheckConstraint(
            "(annotation_id IS NOT NULL AND source_reference_id IS NULL) OR "
            "(annotation_id IS NULL AND source_reference_id IS NOT NULL)",
            name="ck_paper_relation_evidence_exactly_one_source",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paper_relations.id", ondelete="CASCADE"), index=True)
    annotation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("annotations.id", ondelete="CASCADE"), nullable=True, index=True)
    source_reference_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), nullable=True, index=True)
    quote_snapshot: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaperRelationSuggestion(Base):
    __tablename__ = "paper_relation_suggestions"
    __table_args__ = (
        CheckConstraint("relation_type IN ('extends','improves','contrasts','supports','uses','similar')", name="ck_relation_suggestion_type"),
        CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_relation_suggestion_status"),
        CheckConstraint("source_paper_id <> target_paper_id", name="ck_relation_suggestion_not_self"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    target_paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    provider_name: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(255))
    accepted_relation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paper_relations.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
