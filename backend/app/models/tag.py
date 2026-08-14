import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_tag_user_normalized_name"),
        Index("ix_tags_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    )

    user: Mapped["User"] = relationship("User", back_populates="tags")
    papers: Mapped[list["PaperTag"]] = relationship(
        "PaperTag", back_populates="tag", cascade="all, delete-orphan"
    )


class PaperTag(Base):
    """Many-to-many: papers can have multiple tags."""

    __tablename__ = "paper_tags"
    __table_args__ = (
        UniqueConstraint("paper_id", "tag_id", name="uq_paper_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True
    )

    paper: Mapped["Paper"] = relationship("Paper", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="papers")
