import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reference(Base):
    """A PDF-derived bibliography entry; it is never an imported Paper."""

    __tablename__ = "references"
    __table_args__ = (
        UniqueConstraint("document_id", "order_index", name="uq_references_document_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    venue: Mapped[str | None] = mapped_column(Text, nullable=True)

    matched_paper_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("papers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="references")
    section: Mapped["Section | None"] = relationship("Section", back_populates="references")
    matched_paper: Mapped["Paper | None"] = relationship(
        "Paper", back_populates="matched_references", foreign_keys=[matched_paper_id]
    )
