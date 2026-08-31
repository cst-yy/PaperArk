from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.repositories.paper_repository import normalize_orcid


class ResearchIdentityUpdate(BaseModel):
    author_id: UUID
    display_name: str | None = Field(None, max_length=255)
    orcid: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)

    @field_validator("orcid")
    @classmethod
    def canonical_orcid(cls, value: str | None) -> str | None:
        if not value or not value.strip(): return None
        normalized = normalize_orcid(value)
        if normalized is None: raise ValueError("ORCID 格式无效")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if not value or not value.strip(): return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"): raise ValueError("邮箱格式无效")
        return normalized


class ResearchIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    author_id: UUID
    author_name: str
    display_name: str
    orcid: str | None
    email: str | None
    created_at: datetime
    updated_at: datetime


class ResearchIdentityCandidate(BaseModel):
    author_id: UUID
    name: str
    orcid: str | None
    affiliation: str | None
    paper_count: int


class MyPaperStats(BaseModel):
    total: int
    first_or_co_first: int
    corresponding: int
    other: int
