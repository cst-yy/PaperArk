import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PageBlock(Base):
    __tablename__ = "page_blocks"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", "block_order", name="uq_page_blocks_document_page_order"),
        Index("ix_page_blocks_document_reading", "document_id", "page_number", "reading_order"),
        Index("ix_page_blocks_document_page_name", "document_id", "page_number", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    block_order: Mapped[int] = mapped_column(Integer)
    reading_order: Mapped[int] = mapped_column(Integer)
    block_type: Mapped[str] = mapped_column(String(32), default="paragraph", server_default="paragraph")
    name: Mapped[str] = mapped_column(String(255), default="整页", server_default="整页")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    column_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_block_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("page_blocks.id", ondelete="SET NULL"), nullable=True)
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    text_style: Mapped[dict] = mapped_column(JSON, default=lambda: {"font_size": 12, "color": "#1f2937"}, server_default='{"font_size": 12, "color": "#1f2937"}')
    source_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    parser_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaperTranslation(Base):
    __tablename__ = "paper_translations"
    __table_args__ = (Index("ix_paper_translations_user_paper_active", "user_id", "paper_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    source_pdf_hash: Mapped[str] = mapped_column(String(64))
    source_language: Mapped[str] = mapped_column(String(16), default="en", server_default="en")
    target_language: Mapped[str] = mapped_column(String(16))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True)
    model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(40))
    parser_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    blocks: Mapped[list["TranslationBlock"]] = relationship(back_populates="translation", cascade="all, delete-orphan")


class TranslationBlock(Base):
    __tablename__ = "translation_blocks"
    __table_args__ = (UniqueConstraint("paper_translation_id", "page_block_id", name="uq_translation_block_source"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_translation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paper_translations.id", ondelete="CASCADE"), index=True)
    page_block_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("page_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    machine_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    translation: Mapped[PaperTranslation] = relationship(back_populates="blocks")

    @property
    def effective_translation(self) -> str | None:
        return self.user_translation or self.machine_translation


class TranslationJob(Base):
    __tablename__ = "translation_jobs"
    __table_args__ = (Index("ix_translation_jobs_user_paper_created", "user_id", "paper_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    paper_translation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("paper_translations.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(24))
    scope_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True)
    model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    block_ids: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    total_blocks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completed_blocks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_blocks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TranslationGlossary(Base):
    __tablename__ = "translation_glossary"
    __table_args__ = (UniqueConstraint("user_id", "source_language", "target_language", "source_term", "scope_type", "scope_id", name="uq_translation_glossary_term"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    source_term: Mapped[str] = mapped_column(String(255))
    target_term: Mapped[str | None] = mapped_column(String(255), nullable=True)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    do_not_translate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    scope_type: Mapped[str] = mapped_column(String(20), default="global", server_default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
