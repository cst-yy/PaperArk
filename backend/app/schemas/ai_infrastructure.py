from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=8, max_length=2048)
    api_key: str = Field(min_length=1, max_length=4096)
    is_local: bool = False
    timeout_seconds: int = Field(120, ge=5, le=600)
    max_concurrency: int = Field(2, ge=1, le=32)


class AIProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    base_url: str | None = Field(None, min_length=8, max_length=2048)
    api_key: str | None = Field(None, min_length=1, max_length=4096)
    is_local: bool | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = Field(None, ge=5, le=600)
    max_concurrency: int | None = Field(None, ge=1, le=32)


class AIProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    provider_type: str
    base_url: str
    masked_api_key: str
    is_local: bool
    enabled: bool
    timeout_seconds: int
    max_concurrency: int
    capabilities: dict
    created_at: datetime
    updated_at: datetime


class AIModelCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider_id: UUID
    model_name: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    context_window: int | None = Field(None, ge=1)
    max_output_tokens: int | None = Field(None, ge=1)
    capabilities: dict = Field(default_factory=lambda: {"generation": True, "structured_output": True})


class AIModelPricingCreate(BaseModel):
    currency: str = Field("USD", min_length=3, max_length=8)
    input_per_million: Decimal | None = Field(None, ge=0)
    cached_input_per_million: Decimal | None = Field(None, ge=0)
    output_per_million: Decimal | None = Field(None, ge=0)


class AIModelPricingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    model_id: UUID
    currency: str
    input_per_million: Decimal | None
    cached_input_per_million: Decimal | None
    output_per_million: Decimal | None
    effective_from: datetime
    effective_to: datetime | None


class AIModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    provider_id: UUID
    model_name: str
    display_name: str | None
    context_window: int | None
    max_output_tokens: int | None
    capabilities: dict
    enabled: bool
    # Current effective price, exposed so the settings UI can reflect the
    # selected model immediately instead of retaining the previous model's
    # values in uncontrolled form fields.
    pricing: AIModelPricingResponse | None = None


class AIDefaultModelUpdate(BaseModel):
    model_id: UUID


class AIBudgetCreate(BaseModel):
    scope_type: Literal["global", "provider", "model", "feature", "paper", "translation_job", "chat_session"] = "global"
    scope_id: str | None = Field(None, max_length=255)
    period_type: Literal["per_request", "daily", "weekly", "monthly", "lifetime"]
    token_limit: int | None = Field(None, ge=1)
    cost_limit: Decimal | None = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=8)
    hard_limit: bool = True
    warning_threshold: Decimal = Field(Decimal("0.8"), gt=0, le=1)
    enabled: bool = True

    @field_validator("cost_limit")
    @classmethod
    def at_least_one_limit(cls, value: Decimal | None, info):
        if value is None and info.data.get("token_limit") is None:
            raise ValueError("token_limit or cost_limit is required")
        return value


class AIBudgetResponse(AIBudgetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class AIUsageSummary(BaseModel):
    request_count: int
    success_count: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    calculated_cost: Decimal
    unknown_cost_requests: int
    currency: str | None


class AIRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    feature: str
    operation: str
    status: str
    paper_id: UUID | None
    provider_id: UUID | None
    model_id: UUID | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    token_source: str
    estimated_cost: Decimal | None
    actual_cost: Decimal | None
    currency: str | None
    cost_status: str
    duration_ms: int | None
    safe_error: str | None
    created_at: datetime
    completed_at: datetime | None


class AIRequestPage(BaseModel):
    items: list[AIRequestResponse]
    total: int
    page: int
    page_size: int
