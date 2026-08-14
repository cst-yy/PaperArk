from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.schemas.annotation import AnnotationType


NoteType = Literal["general", "paper", "research"]


class NoteCreate(BaseModel):
    paper_id: UUID | None = None
    title: str = Field(default="Untitled note", min_length=1, max_length=500)
    content_markdown: str = ""
    note_type: NoteType = "general"
    annotation_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_paper_note(self):
        if self.note_type in {"paper", "research"} and self.paper_id is None:
            raise ValueError("paper and research notes require paper_id")
        return self


class NoteUpdate(BaseModel):
    paper_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content_markdown: str | None = None
    note_type: NoteType | None = None


class NoteAggregateSave(BaseModel):
    paper_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    content_markdown: str
    note_type: NoteType

    @model_validator(mode="after")
    def validate_paper_note(self):
        if self.note_type in {"paper", "research"} and self.paper_id is None:
            raise ValueError("paper and research notes require paper_id")
        return self


class NoteResponse(ORMModel):
    id: UUID
    user_id: UUID
    paper_id: UUID | None = None
    title: str
    content_markdown: str
    note_type: NoteType
    created_at: datetime
    updated_at: datetime
    evidence: list["NoteEvidenceResponse"] = Field(default_factory=list)


class EvidenceAnnotationBrief(ORMModel):
    id: UUID
    type: AnnotationType
    selected_text: str | None = None
    comment: str | None = None
    page_number: int
    document_id: UUID
    paper_id: UUID


class NoteEvidenceResponse(ORMModel):
    id: UUID
    annotation_id: UUID
    order_index: int
    quote_snapshot: str | None = None
    created_at: datetime
    annotation: EvidenceAnnotationBrief


class NoteEvidenceReplacement(BaseModel):
    annotation_ids: list[UUID]

    @model_validator(mode="after")
    def reject_duplicates(self):
        if len(set(self.annotation_ids)) != len(self.annotation_ids):
            raise ValueError("annotation_ids must be unique")
        return self


class NoteLinkCreate(BaseModel):
    source_note_id: UUID
    target_note_id: UUID
    link_text: str | None = None


class NoteLinkResponse(ORMModel):
    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_text: str | None = None
