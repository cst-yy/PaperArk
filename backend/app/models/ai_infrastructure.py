import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


MONEY = Numeric(20, 10)


class AIProvider(Base):
    __tablename__ = "ai_providers"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_ai_providers_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(40), default="openai_compatible", server_default="openai_compatible")
    base_url: Mapped[str] = mapped_column(Text)
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, server_default="120")
    max_concurrency: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    models: Mapped[list["AIModel"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_name", name="uq_ai_models_provider_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_providers.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    provider: Mapped[AIProvider] = relationship(back_populates="models")
    prices: Mapped[list["AIModelPricing"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class AIModelPricing(Base):
    __tablename__ = "ai_model_pricing"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_models.id", ondelete="CASCADE"), index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", server_default="USD")
    input_per_million: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cached_input_per_million: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    output_per_million: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    model: Mapped[AIModel] = relationship(back_populates="prices")


class AIRequestRecord(Base):
    __tablename__ = "ai_request_records"
    __table_args__ = (
        Index("ix_ai_requests_user_created", "user_id", "created_at"),
        Index("ix_ai_requests_user_feature_created", "user_id", "feature", "created_at"),
        Index("ix_ai_requests_user_paper_created", "user_id", "paper_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True)
    model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    paper_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    feature: Mapped[str] = mapped_column(String(40), index=True)
    operation: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="reserved", server_default="reserved", index=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_source: Mapped[str] = mapped_column(String(24), default="estimate", server_default="estimate")
    estimated_cost: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    cost_status: Mapped[str] = mapped_column(String(24), default="unknown", server_default="unknown")
    price_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    safe_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    context_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIBudgetPolicy(Base):
    __tablename__ = "ai_budget_policies"
    __table_args__ = (
        CheckConstraint("period_type IN ('per_request','daily','weekly','monthly','lifetime')", name="ck_ai_budget_period"),
        UniqueConstraint("user_id", "scope_type", "scope_id", "period_type", name="uq_ai_budget_scope_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="global", server_default="global")
    scope_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_type: Mapped[str] = mapped_column(String(20))
    token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_limit: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", server_default="USD")
    hard_limit: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    warning_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.8"), server_default="0.8")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIBudgetReservation(Base):
    __tablename__ = "ai_budget_reservations"
    __table_args__ = (Index("ix_ai_reservations_user_status_expiry", "user_id", "status", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_request_records.id", ondelete="CASCADE"), index=True)
    budget_policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_budget_policies.id", ondelete="CASCADE"), index=True)
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved_cost: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
