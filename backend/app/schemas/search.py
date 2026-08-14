"""Stable S8 search contracts shared by providers, aggregation, and the API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SearchSource = Literal[
    "title", "abstract", "author", "tag", "keyword", "doi", "arxiv",
    "journal", "conference", "publisher", "section", "chunk", "reference",
    "figure", "table",
]
SearchMatchType = Literal["exact", "prefix", "fuzzy", "fulltext"]


class SearchHit(BaseModel):
    paper_id: UUID
    document_id: UUID | None = None
    source: SearchSource
    text: str
    snippet: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_id: UUID | None = None
    raw_score: float = 0.0
    match_type: SearchMatchType = "fulltext"


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
    paper: SearchPaperBrief
    score: float
    match_count: int
    matches: list[SearchMatchResponse]


class SearchPageResponse(BaseModel):
    items: list[SearchPaperResult]
    total: int
    page: int
    page_size: int
