from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CitationGraphNode(BaseModel):
    paper_id: UUID
    title: str
    publication_year: int | None = None
    authors: list[str]
    is_starred: bool
    reading_status: str
    incoming_count: int
    outgoing_count: int


class CitationGraphEdge(BaseModel):
    relation_id: UUID
    source_paper_id: UUID
    target_paper_id: UUID
    relation_type: Literal["cites"]
    origin: Literal["reference"]
    confidence: float | None = None
    source_reference_id: UUID | None = None


class CitationGraphResponse(BaseModel):
    root_paper_id: UUID | None = None
    depth: Literal[1, 2]
    nodes: list[CitationGraphNode]
    edges: list[CitationGraphEdge]
    truncated: bool
    total_nodes: int


class CitationEdgeDetail(BaseModel):
    edge: CitationGraphEdge
    raw_citation: str | None = None
    reference_order: int | None = None
    match_method: str | None = None
