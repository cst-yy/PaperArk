import uuid
from pydantic import BaseModel, Field, field_validator

COLOR = r"^#[0-9A-Fa-f]{6}$"

class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    color: str | None = Field(default=None, pattern=COLOR)
    icon: str | None = Field(default=None, max_length=50)
    @field_validator("name")
    @classmethod
    def clean(cls, value: str):
        value=value.strip()
        if not value: raise ValueError("name cannot be empty")
        return value

class FolderUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    color: str | None = Field(default=None, pattern=COLOR)
    icon: str | None = Field(default=None, max_length=50)
    parent_id: uuid.UUID | None = None
    @field_validator("name")
    @classmethod
    def clean(cls, value: str | None):
        if value is None: return None
        value=value.strip()
        if not value: raise ValueError("name cannot be empty")
        return value

class FolderResponse(BaseModel):
    id: uuid.UUID; name: str; parent_id: uuid.UUID | None = None; color: str | None = None; icon: str | None = None; sort_order: int; revision: int; paper_count: int = 0; children: list["FolderResponse"] = []
    model_config={"from_attributes":True}
