import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Section(Base):
    """Represents a structural section of a document (e.g., chapter, subsection)."""

    __tablename__ = "sections"
    __table_args__ = (Index("ix_sections_search_vector", "search_vector", postgresql_using="gin"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(Text)
    section_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # chapter | section | subsection | paragraph | abstract | references
    level: Mapped[int] = mapped_column(Integer, default=0)

    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))", persisted=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="sections")
    parent: Mapped["Section | None"] = relationship(
        "Section", remote_side="Section.id", back_populates="children"
    )
    children: Mapped[list["Section"]] = relationship(
        "Section", back_populates="parent", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="section", cascade="all, delete-orphan"
    )
    references: Mapped[list["Reference"]] = relationship(
        "Reference", back_populates="section"
    )
    elements: Mapped[list["DocumentElement"]] = relationship(
        "DocumentElement", back_populates="section"
    )
