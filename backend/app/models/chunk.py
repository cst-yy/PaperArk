import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class Chunk(Base):
    """A text chunk extracted from a document - the core unit for AI/RAG."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_order"),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )

    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    content: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', coalesce(content, ''))", persisted=True)
    )
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Bounding box for PDF position recovery: [x0, y0, x1, y1]
    bbox: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vector embedding for semantic search
    if HAS_PGVECTOR:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(settings.EMBEDDING_DIMENSION), nullable=True
        )
    else:
        embedding = None

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    section: Mapped["Section | None"] = relationship("Section", back_populates="chunks")
