"""Stable S8 search contracts shared by providers, aggregation, and the API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SearchSource = Literal[
    "title", "abstract", "author", "tag", "keyword", "doi", "arxiv",
    "journal", "conference", "publisher", "section", "chunk", "reference",
    "figure", "table", "note_title", "note_content", "research_background",
    "research_problem", "research_method", "research_contribution",
    "research_experiment", "research_conclusion", "research_thought",
]
SearchMatchType = Literal["exact", "prefix", "fuzzy", "fulltext"]
RetrievalMethod = Literal["lexical", "semantic"]


class SearchHit(BaseModel):
    entity_type: Literal["paper", "note"] = "paper"
    paper_id: UUID | None = None
    note_id: UUID | None = None
    document_id: UUID | None = None
    source: SearchSource
    text: str
    snippet: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_id: UUID | None = None
    raw_score: float = 0.0
    match_type: SearchMatchType = "fulltext"
    retrieval_method: RetrievalMethod = "lexical"


class SearchMatchResponse(BaseModel):
    source: SearchSource
    text: str
    snippet: str | None = None
    document_id: UUID | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_id: UUID | None = None


class SearchPaperBrief(BaseModel):
    id: UUID
    title: str
    publication_year: int | None = None
    authors: list[str] = []


class SearchPaperResult(BaseModel):
    entity_type: Literal["paper"] = "paper"
    paper: SearchPaperBrief
    score: float
    match_count: int
    matches: list[SearchMatchResponse]


class SearchNoteBrief(BaseModel):
    id: UUID
    title: str
    note_type: Literal["general", "paper", "research"]
    paper_id: UUID | None = None
    paper_title: str | None = None


class SearchNoteResult(BaseModel):
    entity_type: Literal["note"] = "note"
    note: SearchNoteBrief
    score: float
    match_count: int
    matches: list[SearchMatchResponse]


class SearchRetrievalMetadata(BaseModel):
    requested_mode: Literal["lexical", "semantic", "hybrid"]
    effective_mode: Literal["lexical", "semantic", "hybrid"]
    semantic_available: bool
    semantic_index_ready: bool


class SearchPageResponse(BaseModel):
    items: list[SearchPaperResult | SearchNoteResult]
    total: int
    page: int
    page_size: int
    retrieval: SearchRetrievalMetadata | None = None
