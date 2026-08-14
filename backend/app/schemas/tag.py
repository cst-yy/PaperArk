from uuid import UUID

from pydantic import BaseModel, field_validator


class TagCreate(BaseModel):
    name: str
    color: str | None = None

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标签名称不能为空")
        return value


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None

    @field_validator("name")
    @classmethod
    def require_name_when_present(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("标签名称不能为空")
        return value


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str | None = None
    paper_count: int = 0

    model_config = {"from_attributes": True}
