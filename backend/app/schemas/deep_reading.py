from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai import AICitation
from app.schemas.rag import RAGMode


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
