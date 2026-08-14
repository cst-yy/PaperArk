import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    """Represents a PDF file associated with a paper.

    Document.file_path is the authoritative source for the file location.
    Paper.pdf_path is deprecated and kept only for backward compatibility.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    # File metadata
    original_filename: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # e.g. "Attention Is All You Need.pdf"
    file_path: Mapped[str] = mapped_column(Text)  # e.g. "pdfs/uuid.pdf"
    file_size: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )  # bytes; BigInteger for future-proofing
    mime_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "application/pdf"
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # SHA-256 of original bytes; historic documents may be NULL

    # Parse metadata (S7/S10 will populate these)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", index=True
    )  # pending | processing | ready | failed
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    parser_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="documents")
    sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    references: Mapped[list["Reference"]] = relationship(
        "Reference", back_populates="document", cascade="all, delete-orphan"
    )
    elements: Mapped[list["DocumentElement"]] = relationship(
        "DocumentElement", back_populates="document", cascade="all, delete-orphan"
    )
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(
        "ReadingProgress", back_populates="document", cascade="all, delete-orphan"
    )
