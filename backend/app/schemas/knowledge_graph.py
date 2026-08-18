from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.citation_graph import CitationGraphNode
from app.schemas.knowledge_relation import KnowledgeRelationType


class KnowledgeGraphEdge(BaseModel):
    relation_id: UUID
    source_paper_id: UUID
    target_paper_id: UUID
    relation_type: KnowledgeRelationType | Literal["cites"]
    origin: Literal["reference", "manual", "ai"]
    confidence: float | None = None
    note: str | None = None
    evidence_count: int = 0


class KnowledgeGraphResponse(BaseModel):
    root_paper_id: UUID | None = None
    depth: Literal[1, 2]
    nodes: list[CitationGraphNode]
    edges: list[KnowledgeGraphEdge]
    truncated: bool
    total_nodes: int

