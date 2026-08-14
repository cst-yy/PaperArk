from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings

RAGMode = Literal["lexical", "semantic", "hybrid"]


class RAGContextRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    mode: RAGMode = "lexical"
    paper_id: UUID | None = None
    max_sources: int = Field(settings.RAG_DEFAULT_MAX_SOURCES, ge=1, le=20)
    token_budget: int = Field(settings.RAG_DEFAULT_TOKEN_BUDGET, ge=1000, le=settings.RAG_MAX_TOKEN_BUDGET)


class RAGSource(BaseModel):
    source_key: str
    source_type: Literal["paper_chunk", "note"]
    paper_id: UUID | None = None
    paper_title: str | None = None
    document_id: UUID | None = None
    note_id: UUID | None = None
    section_id: UUID | None = None
    section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    title: str
    content: str
    retrieval_method: Literal["lexical", "semantic", "hybrid"]
    retrieval_score: float | None = None
    estimated_tokens: int
    truncated: bool = False


class RAGContextResponse(BaseModel):
    query: str
    requested_mode: RAGMode
    effective_mode: RAGMode
    degraded: bool
    semantic_available: bool
    semantic_index_ready: bool
    sources: list[RAGSource]
    context_text: str
    estimated_tokens: int
    truncated: bool
