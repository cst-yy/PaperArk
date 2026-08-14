import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaperRelation(Base):
    """Relationships between papers: cites, cited_by, related, extends, etc."""

    __tablename__ = "paper_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_paper_id",
            "target_paper_id",
            "relation_type",
            name="uq_paper_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    target_paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    # cites | cited_by | related | same_topic | extends | improves | baseline
    relation_type: Mapped[str] = mapped_column(String(50))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

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
