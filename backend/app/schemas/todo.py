from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    due_at: datetime | None = None
    related_paper_id: UUID | None = None
    position: int = Field(default=0, ge=0)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title cannot be empty")
        return value


class TodoUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    completed: bool | None = None
    priority: str | None = Field(default=None, pattern="^(low|normal|high)$")
    due_at: datetime | None = None
    related_paper_id: UUID | None = None
    position: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def clean_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("title cannot be empty")
        return value


class TodoResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    completed: bool
    priority: str
    due_at: datetime | None
    related_paper_id: UUID | None
    related_paper_title: str | None = None
    position: int
    revision: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
