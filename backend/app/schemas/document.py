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


class DocumentResponse(ORMModel):
    id: UUID
    paper_id: UUID
    original_filename: str | None = None
    file_path: str
    file_size: int | None = None
    mime_type: str | None = None
    page_count: int | None = None
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
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
    children: list["SectionResponse"] = []


class ChunkResponse(ORMModel):
    id: UUID
    document_id: UUID
    section_id: UUID | None = None
    page_number: int | None = None
    chunk_index: int
    content: str
    token_count: int | None = None
