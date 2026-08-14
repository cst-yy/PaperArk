import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Annotation(Base):
    """A durable PDF evidence anchor.

    Text and area annotations use normalized page coordinates in ``position_data``
    so they remain stable across zoom, Fit Width, and viewport resizing.
    """

    __tablename__ = "annotations"
    __table_args__ = (
        Index("ix_annotations_user_paper_page", "user_id", "paper_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    type: Mapped[str] = mapped_column(String(20))  # highlight | underline | comment | area
    # Backward-compatible comment field. New clients should use ``comment``.
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, index=True)

    # Legacy fields retained so prior annotations remain readable.
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[str | None] = mapped_column(Text, nullable=True)

    selected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefix_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suffix_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="annotations")
    paper: Mapped["Paper"] = relationship("Paper", back_populates="annotations")
