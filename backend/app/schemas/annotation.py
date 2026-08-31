from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ORMModel

AnnotationType = Literal["highlight", "underline", "comment", "area"]
AnnotationColor = Literal["yellow", "green", "blue", "red", "purple"]
AnnotationLineStyle = Literal["solid", "dashed", "dotted", "double", "wavy"]


class AnnotationCreate(BaseModel):
    paper_id: UUID
    document_id: UUID
    type: AnnotationType
    page_number: int = Field(ge=1)
    selected_text: str | None = None
    prefix_text: str | None = None
    suffix_text: str | None = None
    position_data: dict[str, Any] | None = None
    color: AnnotationColor | None = None
    line_style: AnnotationLineStyle | None = None
    comment: str | None = None

    # Compatibility inputs for annotations saved by the earlier reader prototype.
    content: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    bbox: str | None = None

    @field_validator("position_data")
    @classmethod
    def validate_position_data(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        kind = value.get("kind")
        if kind not in {"text", "area"}:
            raise ValueError("position_data.kind must be 'text' or 'area'")
        return value

    @model_validator(mode="after")
    def validate_anchor(self) -> "AnnotationCreate":
        if self.type == "area":
            if self.position_data is None or self.position_data.get("kind") != "area":
                raise ValueError("area annotations require an area position_data anchor")
        elif self.type in {"highlight", "underline"}:
            if not self.selected_text or self.position_data is None or self.position_data.get("kind") != "text":
                raise ValueError("text annotations require selected_text and a text position_data anchor")
        return self


class AnnotationUpdate(BaseModel):
    color: AnnotationColor | None = None
    line_style: AnnotationLineStyle | None = None
    comment: str | None = None


class AnnotationResponse(ORMModel):
    id: UUID
    paper_id: UUID
    document_id: UUID
    type: AnnotationType
    page_number: int
    selected_text: str | None = None
    prefix_text: str | None = None
    suffix_text: str | None = None
    position_data: dict[str, Any] | None = None
    color: AnnotationColor | None = None
    line_style: AnnotationLineStyle | None = None
    comment: str | None = None
    content: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    bbox: str | None = None
    created_at: datetime
    updated_at: datetime
