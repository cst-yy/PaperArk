from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

COLOR_PATTERN = r"^(#[0-9A-Fa-f]{6})$"


class MemoCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    pinned: bool = False
    related_paper_id: UUID | None = None

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content cannot be empty")
        return value


class MemoUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    pinned: bool | None = None
    related_paper_id: UUID | None = None

    @field_validator("content")
    @classmethod
    def clean_optional_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("content cannot be empty")
        return value


class MemoResponse(BaseModel):
    id: UUID
    content: str
    color: str | None
    pinned: bool
    related_paper_id: UUID | None
    related_paper_title: str | None = None
    revision: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
