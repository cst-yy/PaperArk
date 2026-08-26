from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.paper import AuthorBrief, ReadingStatus

PaperListSort = Literal["title", "title_zh", "publication_year", "journal", "conference", "citation_count", "reading_status", "created_at", "updated_at"]
SortOrder = Literal["asc", "desc"]
PaperListColumn = Literal["title", "title_zh", "abstract", "authors", "journal", "conference", "publication_year", "keywords", "tags", "folders", "doi", "arxiv_id", "url", "publisher", "citation_text", "citation_count", "reading_status", "starred", "notes", "created_at", "updated_at"]


class PaperListNamedItem(BaseModel):
    id: UUID
    name: str


class PaperListRow(BaseModel):
    id: UUID
    title: str
    title_zh: str | None = None
    authors: list[AuthorBrief] = []
    journal: str | None = None
    conference: str | None = None
    publication_year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    publisher: str | None = None
    abstract: str | None = None
    citation_text: str | None = None
    citation_count: int | None = None
    keywords: list[PaperListNamedItem] = []
    tags: list[PaperListNamedItem] = []
    folders: list[PaperListNamedItem] = []
    status: str
    reading_status: ReadingStatus
    starred: bool
    note_count: int
    has_document: bool
    created_at: datetime
    updated_at: datetime
    metadata_revision: int


class PaperListPage(BaseModel):
    items: list[PaperListRow]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaperListAppearance(BaseModel):
    font_family: Literal["system", "Arial", "Helvetica", "Times New Roman", "Georgia", "Noto Sans", "Noto Serif"] = "system"
    font_size: Literal["small", "normal", "large"] = "normal"
    density: Literal["compact", "normal", "relaxed"] = "compact"
    header_background: str = "#F8FAFC"
    header_text: str = "#475569"
    row_background: str = "#FFFFFF"
    alternate_row_background: str = "#F8FAFC"
    selected_background: str = "#E0E7FF"
    hover_background: str = "#EEF2FF"
    primary_text: str = "#0F172A"
    secondary_text: str = "#64748B"
    border: str = "#E2E8F0"
    link: str = "#4F46E5"

    @field_validator("header_background", "header_text", "row_background", "alternate_row_background", "selected_background", "hover_background", "primary_text", "secondary_text", "border", "link")
    @classmethod
    def validate_hex(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError("Color must use #RRGGBB")
        return value.upper()


class PaperListPreference(BaseModel):
    visible_columns: list[str] = []
    column_order: list[str] = []
    appearance: PaperListAppearance = PaperListAppearance()


class ColumnWidthPreference(BaseModel):
    preferred_width: int = Field(ge=36, le=800)
    mode: Literal["auto", "manual"] = "auto"


class PaperListColumnsSettings(BaseModel):
    visible: list[PaperListColumn] = []
    order: list[PaperListColumn] = []
    widths: dict[PaperListColumn, ColumnWidthPreference] = {}
    layout_version: int = 1

    @field_validator("visible", "order", mode="after")
    @classmethod
    def unique_columns(cls, value):
        return list(dict.fromkeys(value))[:32]


class PaperListQuerySettings(BaseModel):
    q: str | None = Field(None, max_length=300)
    year_from: int | None = Field(None, ge=1000, le=9999)
    year_to: int | None = Field(None, ge=1000, le=9999)
    journal: str | None = Field(None, max_length=255)
    author: str | None = Field(None, max_length=255)
    tag_id: UUID | None = None
    keyword: str | None = Field(None, max_length=255)
    reading_status: ReadingStatus | None = None
    starred: bool | None = None
    sort: PaperListSort = "updated_at"
    order: SortOrder = "desc"
    page: int = Field(1, ge=1, le=100000)
    page_size: Literal[25, 50, 100, 200] = 50


class PaperListLayoutSettings(BaseModel):
    filters_expanded: bool = True
    display_sections_expanded: list[str] = []
    last_paper_id: UUID | None = None
    scroll_top: int = Field(0, ge=0, le=10_000_000)

    @field_validator("display_sections_expanded", mode="after")
    @classmethod
    def safe_sections(cls, value: list[str]) -> list[str]:
        allowed = {"typography", "colors", "columns"}
        return [item for item in dict.fromkeys(value) if item in allowed]


class PaperListViewSettings(BaseModel):
    schema_version: Literal[2] = 2
    revision: int = Field(0, ge=0)
    columns: PaperListColumnsSettings = PaperListColumnsSettings()
    appearance: PaperListAppearance = PaperListAppearance()
    query: PaperListQuerySettings = PaperListQuerySettings()
    layout: PaperListLayoutSettings = PaperListLayoutSettings()


class PaperListViewSettingsPatch(BaseModel):
    expected_revision: int = Field(ge=0)
    columns: PaperListColumnsSettings | None = None
    appearance: PaperListAppearance | None = None
    query: PaperListQuerySettings | None = None
    layout: PaperListLayoutSettings | None = None

    @model_validator(mode="after")
    def exactly_one_section(self):
        values = [self.columns, self.appearance, self.query, self.layout]
        if sum(value is not None for value in values) != 1:
            raise ValueError("Exactly one settings section must be supplied")
        return self


class BatchPaperUpdate(BaseModel):
    paper_ids: list[UUID] = Field(min_length=1, max_length=200)
    reading_status: ReadingStatus | None = None
    starred: bool | None = None
    add_tag_ids: list[UUID] = []
    remove_tag_ids: list[UUID] = []
    add_folder_ids: list[UUID] = []
    remove_folder_ids: list[UUID] = []

    @field_validator("paper_ids", "add_tag_ids", "remove_tag_ids", "add_folder_ids", "remove_folder_ids", mode="after")
    @classmethod
    def unique_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class BatchPaperDelete(BaseModel):
    paper_ids: list[UUID] = Field(min_length=1, max_length=200)

    @field_validator("paper_ids", mode="after")
    @classmethod
    def unique_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))
