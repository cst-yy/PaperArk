from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class KeywordInput(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("关键词名称不能为空")
        return value


class KeywordReplacement(BaseModel):
    keywords: list[KeywordInput] = []

    @field_validator("keywords", mode="after")
    @classmethod
    def deduplicate_names(cls, values: list[KeywordInput]) -> list[KeywordInput]:
        result: list[KeywordInput] = []
        seen: set[str] = set()
        for keyword in values:
            normalized = keyword.name.strip().casefold()
            if normalized not in seen:
                seen.add(normalized)
                result.append(keyword)
        return result


class KeywordResponse(BaseModel):
    id: UUID
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperKeywordBrief(BaseModel):
    id: UUID
    display_name: str
    sources: list[str]
