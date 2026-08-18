import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AIAnalysis(Base):
    """Immutable, derived generation artifact. It is never user-authored knowledge."""

    __tablename__ = "ai_analyses"
    __table_args__ = (
        CheckConstraint("analysis_type IN ('deep_reading')", name="ck_ai_analysis_type"),
        CheckConstraint("status IN ('ready')", name="ck_ai_analysis_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    analysis_type: Mapped[str] = mapped_column(String(30), default="deep_reading", server_default="deep_reading")
    status: Mapped[str] = mapped_column(String(20), default="ready", server_default="ready")
    provider_name: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(100))
    retrieval_mode: Mapped[str] = mapped_column(String(20))
    source_snapshot_hash: Mapped[str] = mapped_column(String(64), index=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sources: Mapped[list["AIAnalysisSource"]] = relationship(
        "AIAnalysisSource", cascade="all, delete-orphan", passive_deletes=True,
        order_by="AIAnalysisSource.order_index", lazy="selectin",
    )
    applications: Mapped[list["AIAnalysisApplication"]] = relationship(
        "AIAnalysisApplication", cascade="all, delete-orphan", passive_deletes=True,
    )


class AIAnalysisSource(Base):
    __tablename__ = "ai_analysis_sources"
    __table_args__ = (
        UniqueConstraint("analysis_id", "order_index", name="uq_ai_analysis_source_order"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_analyses.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    source_key: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(30))
    paper_id: Mapped[uuid.UUID] = mapped_column(index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(1000))
    content_snapshot: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class AIAnalysisApplication(Base):
    __tablename__ = "ai_analysis_applications"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_analyses.id", ondelete="CASCADE"), index=True)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    application_mode: Mapped[str] = mapped_column(String(100))
    applied_fields_json: Mapped[dict] = mapped_column(JSON)
    profile_revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
