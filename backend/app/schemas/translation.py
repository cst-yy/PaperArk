from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


TranslationScope = Literal["selection", "blocks", "page", "section", "from_page", "paper"]


class TranslationEstimateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    document_id: UUID
    scope_type: TranslationScope
    page_number: int | None = Field(None, ge=1)
    section_id: UUID | None = None
    block_ids: list[UUID] = Field(default_factory=list, max_length=5000)
    target_language: str = Field("zh-CN", min_length=2, max_length=16)
    model_id: UUID | None = None


class TranslationEstimateResponse(BaseModel):
    total_blocks: int
    reusable_blocks: int
    pending_blocks: int
    source_characters: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: Decimal | None
    currency: str | None
    price_available: bool


class TranslationCreateRequest(TranslationEstimateRequest):
    confirmed: bool
    max_cost: Decimal | None = Field(None, ge=0)


class PageBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    paper_id: UUID
    section_id: UUID | None
    page_number: int
    block_order: int
    reading_order: int
    block_type: str
    column_index: int | None
    bounding_box: dict | None
    source_text: str
    source_hash: str


class TranslationBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    page_block_id: UUID | None
    source_hash: str
    machine_translation: str | None
    user_translation: str | None
    status: str
    revision: int
    translated_at: datetime | None

    @computed_field
    @property
    def effective_translation(self) -> str | None:
        return self.user_translation or self.machine_translation


class PaperTranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    paper_id: UUID
    document_id: UUID
    source_language: str
    target_language: str
    status: str
    is_active: bool
    created_at: datetime
    completed_at: datetime | None


class TranslationPageResponse(BaseModel):
    translation: PaperTranslationResponse | None
    blocks: list[PageBlockResponse]
    translations: list[TranslationBlockResponse]


class TranslationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    paper_id: UUID
    paper_translation_id: UUID
    scope_type: str
    status: str
    total_blocks: int
    completed_blocks: int
    failed_blocks: int
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal | None
    actual_cost: Decimal | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class TranslationBlockUpdate(BaseModel):
    user_translation: str | None = Field(None, max_length=100000)
    expected_revision: int = Field(ge=1)


class GlossaryCreate(BaseModel):
    source_language: str = "en"
    target_language: str = "zh-CN"
    source_term: str = Field(min_length=1, max_length=255)
    target_term: str | None = Field(None, max_length=255)
    case_sensitive: bool = False
    do_not_translate: bool = False
    scope_type: Literal["global", "paper"] = "global"
    scope_id: UUID | None = None


class GlossaryResponse(GlossaryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
