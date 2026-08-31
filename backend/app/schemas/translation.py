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
    name: str
    is_default: bool
    column_index: int | None
    bounding_box: dict | None
    text_style: dict
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


class ManualTranslationBlockSave(BaseModel):
    document_id: UUID
    page_block_id: UUID
    target_language: str = Field("zh-CN", min_length=2, max_length=16)
    user_translation: str = Field(min_length=1, max_length=100000)
    expected_revision: int | None = Field(None, ge=1)


class PageBlockBBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    def as_dict(self) -> dict[str, float]:
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("bounding box is outside the page")
        return self.model_dump()


class CustomPageBlockCreate(BaseModel):
    page_number: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    bounding_box: PageBlockBBox


class PageBlockTextStyle(BaseModel):
    font_size: int = Field(12, ge=8, le=32)
    color: str = Field("#1f2937", pattern=r"^#[0-9a-fA-F]{6}$")


class CustomPageBlockUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    bounding_box: PageBlockBBox | None = None
    text_style: PageBlockTextStyle | None = None


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
