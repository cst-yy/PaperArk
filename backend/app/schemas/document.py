from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class DocumentBrief(BaseModel):
    """Brief document info — returned inside PaperResponse.
    Frontend uses document.id to build /api/documents/{id}/file URL.
    """

    id: UUID
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
    parser_version: str | None = None


class DocumentResponse(ORMModel):
    id: UUID
    paper_id: UUID
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    page_count: int | None = None
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
    parser_version: str | None = None
    created_at: datetime
    updated_at: datetime


class SectionResponse(ORMModel):
    id: UUID
    document_id: UUID
    parent_id: UUID | None = None
    title: str
    section_type: str | None = None
    level: int
    page_start: int | None = None
    page_end: int | None = None
    order_index: int
    raw_text: str | None = None
    children: list["SectionResponse"] = []


class MatchedPaperBrief(BaseModel):
    id: UUID
    title: str


class ReferenceResponse(ORMModel):
    id: UUID
    document_id: UUID
    section_id: UUID | None = None
    order_index: int
    raw_text: str
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    venue: str | None = None
    page_start: int
    page_end: int
    matched_paper: MatchedPaperBrief | None = None
    match_method: str | None = None
    match_confidence: float | None = None


class ElementBBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DocumentElementResponse(ORMModel):
    id: UUID
    document_id: UUID
    section_id: UUID | None = None
    element_type: str
    order_index: int
    page_number: int
    label: str | None = None
    caption: str
    raw_text: str | None = None
    bbox: ElementBBox | None = None
    source: str
    confidence: float | None = None


class ChunkResponse(ORMModel):
    id: UUID
    document_id: UUID
    section_id: UUID | None = None
    page_number: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_index: int
    content: str
    token_count: int | None = None
    char_count: int | None = None
