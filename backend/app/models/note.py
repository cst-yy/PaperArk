import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Computed, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("note_type IN ('general', 'paper', 'research')", name="ck_notes_note_type"),
        Index("ix_notes_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_notes_embedding_hnsw", "embedding", postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}, postgresql_where=text("embedding IS NOT NULL")),
        CheckConstraint("embedding_status IN ('pending', 'processing', 'ready', 'failed')", name="ck_notes_embedding_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), default="Untitled note", server_default="Untitled note")
    content_markdown: Mapped[str] = mapped_column(Text, default="", server_default="")
    note_type: Mapped[str] = mapped_column(String(20), default="general", server_default="general", index=True)
    search_vector: Mapped[object] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content_markdown, ''))", persisted=True)
    )
    if HAS_PGVECTOR:
        embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    else:
        embedding = None
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending", index=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="notes")
    paper: Mapped["Paper | None"] = relationship("Paper", back_populates="notes")

    # Outgoing links: this note -> other notes
    outgoing_links: Mapped[list["NoteLink"]] = relationship(
        "NoteLink",
        back_populates="source_note",
        foreign_keys="NoteLink.source_note_id",
        cascade="all, delete-orphan",
    )
    # Incoming links: other notes -> this note
    incoming_links: Mapped[list["NoteLink"]] = relationship(
        "NoteLink",
        back_populates="target_note",
        foreign_keys="NoteLink.target_note_id",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list["NoteEvidence"]] = relationship(
        "NoteEvidence",
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="NoteEvidence.order_index",
        lazy="selectin",
    )
    research_profile: Mapped["ResearchNoteProfile | None"] = relationship(
        "ResearchNoteProfile", back_populates="note", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class NoteLink(Base):
    """Bidirectional links between notes for knowledge graph."""

    __tablename__ = "note_links"
    __table_args__ = (
        UniqueConstraint("source_note_id", "target_note_id", name="uq_note_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), index=True
    )
    target_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), index=True
    )
    link_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source_note: Mapped["Note"] = relationship(
        "Note", back_populates="outgoing_links", foreign_keys=[source_note_id]
    )
    target_note: Mapped["Note"] = relationship(
        "Note", back_populates="incoming_links", foreign_keys=[target_note_id]
    )


class NoteEvidence(Base):
    """Ordered reference from a research note to a durable Annotation anchor."""

    __tablename__ = "note_evidence"
    __table_args__ = (
        UniqueConstraint("note_id", "annotation_id", name="uq_note_evidence_annotation"),
        UniqueConstraint("note_id", "order_index", name="uq_note_evidence_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    annotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column()
    quote_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    note: Mapped["Note"] = relationship("Note", back_populates="evidence")
    annotation: Mapped["Annotation"] = relationship("Annotation", back_populates="note_evidence", lazy="joined")
