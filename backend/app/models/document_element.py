import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentElement(Base):
    """A PDF-derived figure or table; never a user-created annotation."""

    __tablename__ = "document_elements"
    __table_args__ = (
        CheckConstraint(
            "element_type IN ('figure', 'table')", name="ck_document_elements_type"
        ),
        UniqueConstraint("document_id", "order_index", name="uq_document_elements_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    element_type: Mapped[str] = mapped_column(String(16), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)

    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    caption: Mapped[str] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Normalized PDF coordinates. All four are NULL when a visual region cannot
    # be determined safely; partial bboxes are forbidden by validation.
    x: Mapped[float | None] = mapped_column(nullable=True)
    y: Mapped[float | None] = mapped_column(nullable=True)
    width: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="pdf", server_default="pdf")
    confidence: Mapped[float | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="elements")
    section: Mapped["Section | None"] = relationship("Section", back_populates="elements")
