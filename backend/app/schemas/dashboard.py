from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_papers: int
    reading_papers: int
    finished_papers: int
    research_notes: int


class DashboardRecentReading(BaseModel):
    paper_id: UUID
    title: str
    publication_year: int | None = None
    author: str | None = None
    document_id: UUID
    current_page: int
    total_pages: int
    progress_ratio: float
    last_read_at: datetime


class DashboardRecentPaper(BaseModel):
    id: UUID
    title: str
    publication_year: int | None = None
    author: str | None = None
    reading_status: str
    created_at: datetime
    updated_at: datetime


class DashboardRecentNote(BaseModel):
    id: UUID
    title: str
    note_type: str
    paper_id: UUID | None = None
    paper_title: str | None = None
    updated_at: datetime


class DashboardTopicStat(BaseModel):
    id: UUID
    name: str
    paper_count: int


class DashboardBackup(BaseModel):
    last_backup_at: datetime | None = None


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    recent_reading: list[DashboardRecentReading]
    recent_papers: list[DashboardRecentPaper]
    recent_notes: list[DashboardRecentNote]
    tags: list[DashboardTopicStat]
    keywords: list[DashboardTopicStat]
    backup: DashboardBackup


class ReadingTrendDay(BaseModel):
    date: date
    papers_read: int
    reading_time_seconds: int


class ReadingTrendSummary(BaseModel):
    papers_read: int
    active_days: int
    reading_time_seconds: int


class ReadingTrendResponse(BaseModel):
    days: int
    daily: list[ReadingTrendDay]
    summary: ReadingTrendSummary
