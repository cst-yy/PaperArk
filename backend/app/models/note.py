import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="notes")
    paper: Mapped["Paper"] = relationship("Paper", back_populates="notes")

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
