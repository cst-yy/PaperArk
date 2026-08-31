from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReadingProgressUpsert(BaseModel):
    """The Reader's latest position in one concrete PDF document."""

    document_id: UUID
    current_page: int = Field(ge=1)
    total_pages: int = Field(ge=1)
    reading_time_seconds_delta: int = Field(default=0, ge=0, le=300)

    @model_validator(mode="after")
    def validate_page_range(self) -> "ReadingProgressUpsert":
        if self.current_page > self.total_pages:
            raise ValueError("current_page cannot exceed total_pages")
        return self


class ReadingProgressResponse(BaseModel):
    paper_id: UUID
    document_id: UUID
    current_page: int
    total_pages: int
    progress_ratio: float
    last_read_at: datetime
    reading_time_seconds: int


class RecentReadingPaper(BaseModel):
    id: UUID
    title: str
    publication_year: int | None = None
    authors: list[str] = []
    is_starred: bool
    my_author_roles: dict[str, int | bool] | None = None


class RecentReadingDocument(BaseModel):
    id: UUID


class RecentReadingItem(BaseModel):
    paper: RecentReadingPaper
    document: RecentReadingDocument
    current_page: int
    total_pages: int
    progress_ratio: float
    last_read_at: datetime
