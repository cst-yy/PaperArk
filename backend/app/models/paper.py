import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        CheckConstraint(
            "reading_status IN ('unread', 'reading', 'finished', 'archived')",
            name="ck_papers_reading_status",
        ),
        Index("ix_papers_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_papers_journal_trgm", "journal", postgresql_using="gin", postgresql_ops={"journal": "gin_trgm_ops"}),
        Index("ix_papers_conference_trgm", "conference", postgresql_using="gin", postgresql_ops={"conference": "gin_trgm_ops"}),
        Index("ix_papers_publisher_trgm", "publisher", postgresql_using="gin", postgresql_ops={"publisher": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(Text)
    title_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    journal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="imported", index=True
    )  # imported | processing | ready | failed
    reading_status: Mapped[str] = mapped_column(
        String(20), default="unread", server_default="unread", index=True
    )  # unread | reading | finished | archived
    ai_access_policy: Mapped[str] = mapped_column(
        String(20), default="allow_cloud", server_default="allow_cloud"
    )  # allow_cloud | local_only | disabled

    is_starred: Mapped[bool] = mapped_column(default=False)
    notes_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    authors: Mapped[list["PaperAuthor"]] = relationship(
        "PaperAuthor", back_populates="paper", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="paper", cascade="all, delete-orphan"
    )
    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="paper", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="paper", cascade="all, delete-orphan"
    )
    tags: Mapped[list["PaperTag"]] = relationship(
        "PaperTag", back_populates="paper", cascade="all, delete-orphan"
    )
    folder_assignments: Mapped[list["PaperFolder"]] = relationship(
        "PaperFolder", back_populates="paper", cascade="all, delete-orphan"
    )
    keywords: Mapped[list["PaperKeyword"]] = relationship(
        "PaperKeyword", back_populates="paper", cascade="all, delete-orphan"
    )
    outgoing_relations: Mapped[list["PaperRelation"]] = relationship(
        "PaperRelation",
        back_populates="source_paper",
        foreign_keys="PaperRelation.source_paper_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    incoming_relations: Mapped[list["PaperRelation"]] = relationship(
        "PaperRelation",
        back_populates="target_paper",
        foreign_keys="PaperRelation.target_paper_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    matched_references: Mapped[list["Reference"]] = relationship(
        "Reference", back_populates="matched_paper", foreign_keys="Reference.matched_paper_id"
    )
