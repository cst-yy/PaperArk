from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RelatedPaperBrief(BaseModel):
    id: UUID
    title: str
    publication_year: int | None = None


class PaperRelationResponse(BaseModel):
    id: UUID
    source_paper_id: UUID
    target_paper_id: UUID
    relation_type: Literal["cites"]
    origin: Literal["reference"]
    source_reference_id: UUID | None = None
    confidence: float | None = None
    related_paper: RelatedPaperBrief
    created_at: datetime


class PaperRelationsResponse(BaseModel):
    paper_id: UUID
    incoming_count: int
    outgoing_count: int
    incoming: list[PaperRelationResponse]
    outgoing: list[PaperRelationResponse]
