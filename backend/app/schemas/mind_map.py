from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MindMapNode(BaseModel):
    id: str
    node_type: Literal["paper", "profile_field", "contribution", "experiment"]
    title: str
    summary: str = ""
    paper_id: UUID
    note_id: UUID | None = None
    entity_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class MindMapEdge(BaseModel):
    source: str
    target: str
    relation: Literal["contains", "supports"]


class MindMapResponse(BaseModel):
    paper_id: UUID
    note_id: UUID | None = None
    profile_revision: int | None = None
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
    has_profile: bool
