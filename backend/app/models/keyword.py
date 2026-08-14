import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Keyword(Base):
    """A user-owned academic keyword, intentionally distinct from organizational tags."""

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_keyword_user_normalized_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(150))
    normalized_name: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="keywords")
    paper_links: Mapped[list["PaperKeyword"]] = relationship(
        "PaperKeyword", back_populates="keyword", cascade="all, delete-orphan"
    )


class PaperKeyword(Base):
    """One keyword contribution for a paper; later pipeline stages can add sources."""

    __tablename__ = "paper_keywords"
    __table_args__ = (
        UniqueConstraint("paper_id", "keyword_id", "source", name="uq_paper_keyword_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    keyword_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("keywords.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(20), default="manual")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    paper: Mapped["Paper"] = relationship("Paper", back_populates="keywords")
    keyword: Mapped["Keyword"] = relationship("Keyword", back_populates="paper_links")
