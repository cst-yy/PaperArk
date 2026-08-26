from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas.common import ORMModel
from app.schemas.document import DocumentBrief
from app.schemas.keyword import KeywordInput, PaperKeywordBrief

ReadingStatus = Literal["unread", "reading", "finished", "archived"]


class AuthorBrief(BaseModel):
    id: UUID | None = None
    name: str
    orcid: str | None = None
    affiliation: str | None = None
    author_order: int = 0


class TagBrief(BaseModel):
    id: UUID
    name: str
    color: str | None = None


class FolderBrief(BaseModel):
    id: UUID
    name: str
    color: str | None = None
    icon: str | None = None


class PaperBase(BaseModel):
    title: str
    title_zh: str | None = None
    citation_text: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    journal: str | None = None
    conference: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    citation_count: int | None = None


class PaperCreate(PaperBase):
    authors: list[AuthorBrief] = []
    tag_ids: list[UUID] = []
    folder_ids: list[UUID] = []

    @field_validator("tag_ids", "folder_ids", mode="after")
    @classmethod
    def deduplicate_ids(cls, v: list[UUID]) -> list[UUID]:
        """Remove duplicate IDs while preserving order."""
        return list(dict.fromkeys(v))


class AuthorReplacement(BaseModel):
    authors: list[AuthorBrief] = []

    @field_validator("authors")
    @classmethod
    def require_unique_author_identities(cls, authors: list[AuthorBrief]) -> list[AuthorBrief]:
        seen: set[tuple[str, str | None]] = set()
        for author in authors:
            author.name = author.name.strip()
            author.affiliation = author.affiliation.strip() if author.affiliation else None
            if not author.name:
                raise ValueError("作者姓名不能为空")
            identity = (author.orcid.strip().lower(), None) if author.orcid else (author.name.casefold(), (author.affiliation or "").casefold())
            if identity in seen:
                raise ValueError("作者列表包含重复身份")
            seen.add(identity)
        return authors


class TagReplacement(BaseModel):
    tag_ids: list[UUID] = []

    @field_validator("tag_ids", mode="after")
    @classmethod
    def deduplicate_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class FolderReplacement(BaseModel):
    folder_ids: list[UUID] = []

    @field_validator("folder_ids", mode="after")
    @classmethod
    def deduplicate_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class PaperMetadataReplaceRequest(PaperBase):
    """Complete editor payload, committed as one Paper aggregate transaction."""

    authors: list[AuthorBrief] = []

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value
    tag_ids: list[UUID] = []
    folder_ids: list[UUID] = []
    keywords: list[KeywordInput] = []
    expected_revision: int | None = None

    @field_validator("authors")
    @classmethod
    def require_unique_author_identities(cls, authors: list[AuthorBrief]) -> list[AuthorBrief]:
        return AuthorReplacement(authors=authors).authors

    @field_validator("tag_ids", "folder_ids", mode="after")
    @classmethod
    def deduplicate_ids(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))


class ReadingStatusUpdate(BaseModel):
    reading_status: ReadingStatus


class PaperUpdate(BaseModel):
    expected_revision: int | None = None
    title: str | None = None
    title_zh: str | None = None
    citation_text: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    journal: str | None = None
    conference: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    citation_count: int | None = None
    is_starred: bool | None = None


class PaperResponse(ORMModel):
    id: UUID
    title: str
    title_zh: str | None = None
    citation_text: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    journal: str | None = None
    conference: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    citation_count: int | None = None
    pdf_path: str | None = None
    cover_path: str | None = None
    status: str
    reading_status: ReadingStatus
    is_starred: bool
    created_at: datetime
    updated_at: datetime
    metadata_revision: int
    authors: list[AuthorBrief] = []
    tags: list[TagBrief] = []
    folders: list[FolderBrief] = []
    keywords: list[PaperKeywordBrief] = []
    # ``document`` remains the backward-compatible primary PDF reference.
    document: DocumentBrief | None = None
    # The ordered document list lets Reader honor an explicit document_id scope.
    documents: list[DocumentBrief] = []


class PaperListResponse(ORMModel):
    id: UUID
    title: str
    publication_year: int | None = None
    journal: str | None = None
    conference: str | None = None
    status: str
    reading_status: ReadingStatus
    is_starred: bool
    created_at: datetime
    first_author: str | None = None
    tags: list[TagBrief] = []
    has_document: bool = False


class PaperPageResponse(BaseModel):
    """Paginated paper list response."""
    items: list[PaperListResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
