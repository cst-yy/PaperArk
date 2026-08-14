from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

class ContributionInput(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    problem: str = ""; prior_limitation: str = ""; innovation: str = ""; solution: str = ""
    evidence_summary: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)

class ExperimentInput(BaseModel):
    client_id: str = Field(min_length=1, max_length=100)
    task: str = ""; datasets: list[str] = Field(default_factory=list); baselines: list[str] = Field(default_factory=list); metrics: list[str] = Field(default_factory=list)
    result: str = ""; conclusion: str = ""
    supports_contribution_client_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)

class ResearchProfileAggregate(BaseModel):
    background: str = ""; prior_work_limitations: str = ""; research_problem: str = ""; method_summary: str = ""
    results_summary: str = ""; conclusion: str = ""; limitations: str = ""; my_thoughts: str = ""
    contributions: list[ContributionInput] = Field(default_factory=list)
    experiments: list[ExperimentInput] = Field(default_factory=list)
    @model_validator(mode="after")
    def validate_client_ids(self):
        contribution_ids = [item.client_id for item in self.contributions]
        experiment_ids = [item.client_id for item in self.experiments]
        if len(set(contribution_ids)) != len(contribution_ids) or len(set(experiment_ids)) != len(experiment_ids): raise ValueError("client_id values must be unique")
        known = set(contribution_ids)
        if any(not set(item.supports_contribution_client_ids) <= known for item in self.experiments): raise ValueError("experiment references an unknown contribution client_id")
        if any(len(set(item.evidence_ids)) != len(item.evidence_ids) for item in [*self.contributions, *self.experiments]): raise ValueError("evidence_ids must be unique")
        return self

class ContributionResponse(BaseModel):
    id: UUID; order_index: int; problem: str; prior_limitation: str; innovation: str; solution: str; evidence_summary: str | None
    evidence_ids: list[UUID]
class ExperimentResponse(BaseModel):
    id: UUID; order_index: int; task: str; datasets: list[str]; baselines: list[str]; metrics: list[str]; result: str; conclusion: str
    contribution_ids: list[UUID]; evidence_ids: list[UUID]
class ResearchProfileResponse(BaseModel):
    id: UUID; note_id: UUID; background: str; prior_work_limitations: str; research_problem: str; method_summary: str; results_summary: str; conclusion: str; limitations: str; my_thoughts: str
    contributions: list[ContributionResponse]; experiments: list[ExperimentResponse]; created_at: datetime; updated_at: datetime
