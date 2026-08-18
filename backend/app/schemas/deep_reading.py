from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai import AICitation
from app.schemas.rag import RAGMode
from app.schemas.research_note import ResearchProfileResponse


class GroundedStructuredField(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    grounded: bool = False


class DeepReadingContribution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(min_length=1, max_length=100)
    problem: str = ""
    prior_limitation: str = ""
    innovation: str = ""
    solution: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    grounded: bool = False


class DeepReadingExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(min_length=1, max_length=100)
    task: str = ""
    datasets: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    result: str = ""
    conclusion: str = ""
    supports_contribution_client_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    grounded: bool = False


class DeepReadingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    background: GroundedStructuredField
    prior_work_limitations: GroundedStructuredField
    research_problem: GroundedStructuredField
    method_summary: GroundedStructuredField
    results_summary: GroundedStructuredField
    conclusion: GroundedStructuredField
    limitations: GroundedStructuredField
    future_work: GroundedStructuredField
    contributions: list[DeepReadingContribution] = Field(default_factory=list)
    experiments: list[DeepReadingExperiment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_client_relationships(self):
        contribution_ids = [item.client_id for item in self.contributions]
        experiment_ids = [item.client_id for item in self.experiments]
        if len(contribution_ids) != len(set(contribution_ids)):
            raise ValueError("contribution client_id values must be unique")
        if len(experiment_ids) != len(set(experiment_ids)):
            raise ValueError("experiment client_id values must be unique")
        known = set(contribution_ids)
        if any(not set(item.supports_contribution_client_ids) <= known for item in self.experiments):
            raise ValueError("experiment references an unknown contribution client_id")
        return self


class DeepReadingRequest(BaseModel):
    paper_id: UUID
    retrieval_mode: RAGMode = "hybrid"


class DeepReadingDraft(DeepReadingPayload):
    paper_id: UUID
    requested_mode: RAGMode
    effective_mode: RAGMode
    sources: list[AICitation]
    source_count: int
    analysis_id: UUID | None = None
    provider_name: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    source_snapshot_hash: str | None = None
    input_hash: str | None = None
    created_at: datetime | None = None


class AIAnalysisSourceResponse(BaseModel):
    label: str
    source_key: str
    source_type: str
    paper_id: UUID
    document_id: UUID | None = None
    chunk_id: UUID | None = None
    section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    title: str
    content_snapshot: str
    content_hash: str
    retrieval_score: float | None = None


class AIAnalysisBrief(BaseModel):
    analysis_id: UUID
    analysis_type: Literal["deep_reading"]
    status: Literal["ready"]
    provider_name: str
    model: str
    prompt_version: str
    retrieval_mode: RAGMode
    source_count: int
    application_count: int
    source_snapshot_hash: str
    created_at: datetime


class AIAnalysisDetail(BaseModel):
    draft: DeepReadingDraft
    source_snapshots: list[AIAnalysisSourceResponse]


AIApplicableScalar = Literal[
    "background", "prior_work_limitations", "research_problem", "method_summary",
    "results_summary", "conclusion", "limitations", "future_work",
]


class AIAnalysisApplySelection(BaseModel):
    scalar_fields: list[AIApplicableScalar] = Field(default_factory=list)
    contribution_client_ids: list[str] = Field(default_factory=list)
    experiment_client_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_selections(self):
        for values in (self.scalar_fields, self.contribution_client_ids, self.experiment_client_ids):
            if len(values) != len(set(values)):
                raise ValueError("apply selections must be unique")
        return self


class AIAnalysisApplyRequest(BaseModel):
    note_id: UUID
    apply: AIAnalysisApplySelection
    scalar_conflict_policy: Literal["fill_empty", "replace"] = "fill_empty"
    collections_mode: Literal["append", "replace"] = "append"
    expected_revision: int = Field(ge=0)


class AIAnalysisApplyResponse(BaseModel):
    application_id: UUID
    analysis_id: UUID
    profile: ResearchProfileResponse
