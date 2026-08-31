import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (Index("ix_authors_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    orcid: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    affiliation: Mapped[str | None] = mapped_column(String(512), nullable=True)

    papers: Mapped[list["PaperAuthor"]] = relationship(
        "PaperAuthor", back_populates="author", cascade="all, delete-orphan"
    )


class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    __table_args__ = (UniqueConstraint("paper_id", "author_id", name="uq_paper_author"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), index=True
    )
    author_order: Mapped[int] = mapped_column(Integer, default=0)
    is_co_first: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_corresponding: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    paper: Mapped["Paper"] = relationship("Paper", back_populates="authors")
    author: Mapped["Author"] = relationship("Author", back_populates="papers")


class ResearchIdentity(Base):
    __tablename__ = "research_identities"
    __table_args__ = (UniqueConstraint("user_id", name="uq_research_identity_user"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("authors.id", ondelete="RESTRICT"), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    orcid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author: Mapped["Author"] = relationship("Author")
