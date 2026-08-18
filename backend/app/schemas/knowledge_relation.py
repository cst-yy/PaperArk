from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

KnowledgeRelationType = Literal["extends", "improves", "contrasts", "supports", "uses", "similar"]


class ManualRelationCreate(BaseModel):
    target_paper_id: UUID
    relation_type: KnowledgeRelationType
    note: str | None = Field(None, max_length=4000)


class ManualRelationUpdate(BaseModel):
    target_paper_id: UUID
    relation_type: KnowledgeRelationType
    note: str | None = Field(None, max_length=4000)


class RelationEvidenceInput(BaseModel):
    annotation_id: UUID | None = None
    source_reference_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.annotation_id is None) == (self.source_reference_id is None):
            raise ValueError("exactly one evidence source is required")
        return self


class RelationEvidenceReplacement(BaseModel):
    evidence: list[RelationEvidenceInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_sources(self):
        keys = [(item.annotation_id, item.source_reference_id) for item in self.evidence]
        if len(keys) != len(set(keys)):
            raise ValueError("evidence sources must be unique")
        return self


class RelationEvidenceResponse(BaseModel):
    id: UUID
    annotation_id: UUID | None = None
    source_reference_id: UUID | None = None
    quote_snapshot: str
    order_index: int
    paper_id: UUID | None = None
    document_id: UUID | None = None
    page_number: int | None = None


class KnowledgeRelationResponse(BaseModel):
    id: UUID
    source_paper_id: UUID
    target_paper_id: UUID
    relation_type: str
    origin: str
    note: str | None = None
    confidence: float | None = None
    evidence: list[RelationEvidenceResponse] = Field(default_factory=list)
    ai_evidence: list[dict] = Field(default_factory=list)
    ai_provider_name: str | None = None
    ai_model: str | None = None
    created_at: datetime


class RelationSuggestionResponse(BaseModel):
    id: UUID
    source_paper_id: UUID
    target_paper_id: UUID
    relation_type: KnowledgeRelationType
    status: Literal["pending", "accepted", "rejected"]
    confidence: float | None = None
    reason: str
    evidence: list[dict]
    provider_name: str
    model: str
    accepted_relation_id: UUID | None = None
    created_at: datetime
    decided_at: datetime | None = None


class RelationSuggestionGenerateRequest(BaseModel):
    max_candidates: int = Field(5, ge=1, le=10)


class AIRelationDecision(BaseModel):
    relation_type: Literal["extends", "improves", "contrasts", "supports", "uses", "similar", "none"]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=4000)
    evidence_refs: list[str] = Field(default_factory=list)
