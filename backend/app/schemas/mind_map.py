from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MindMapNode(BaseModel):
    id: str
    node_type: Literal["paper", "profile_field", "contribution", "experiment", "manual"]
    title: str
    summary: str = ""
    paper_id: UUID
    note_id: UUID | None = None
    entity_id: UUID | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class MindMapEdge(BaseModel):
    id: UUID | None = None
    source: str
    target: str
    relation: str
    manual: bool = False


class ManualMindMapNodeCreate(BaseModel):
    title: str = Field(default="", max_length=500)
    summary: str = Field(default="", max_length=10000)


class ManualMindMapNodeUpdate(ManualMindMapNodeCreate):
    pass


class ManualMindMapEdgeCreate(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=200)
    relation: str = Field(default="关联", min_length=1, max_length=100)


class ManualMindMapEdgeUpdate(BaseModel):
    relation: str = Field(min_length=1, max_length=100)


class MindMapResponse(BaseModel):
    paper_id: UUID
    note_id: UUID | None = None
    profile_revision: int | None = None
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
    has_profile: bool
