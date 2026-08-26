import uuid
from datetime import date, datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Author, Document, Keyword, Note, Paper, PaperAuthor, PaperKeyword,
    PaperTag, ReadingActivity, ReadingProgress, Tag,
)


class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _first_author():
        return (
            select(Author.name)
            .join(PaperAuthor, PaperAuthor.author_id == Author.id)
            .where(PaperAuthor.paper_id == Paper.id)
            .order_by(PaperAuthor.author_order, PaperAuthor.id)
            .limit(1)
            .correlate(Paper)
            .scalar_subquery()
        )

    async def overview(self, user_id: uuid.UUID) -> tuple[int, int, int, int]:
        paper_counts = await self.db.execute(
            select(
                func.count(Paper.id),
                func.count(Paper.id).filter(Paper.reading_status == "reading"),
                func.count(Paper.id).filter(Paper.reading_status == "finished"),
            ).where(Paper.user_id == user_id)
        )
        total, reading, finished = paper_counts.one()
        note_count = await self.db.scalar(
            select(func.count(Note.id)).where(Note.user_id == user_id)
        )
        return int(total), int(reading), int(finished), int(note_count or 0)

    async def recent_reading(self, user_id: uuid.UUID, limit: int = 5):
        author = self._first_author().label("author")
        result = await self.db.execute(
            select(
                Paper.id.label("paper_id"), Paper.title, Paper.publication_year,
                author, ReadingProgress.document_id, ReadingProgress.current_page,
                ReadingProgress.total_pages, ReadingProgress.progress_ratio,
                ReadingProgress.last_read_at,
            )
            .join(Document, Document.paper_id == Paper.id)
            .join(ReadingProgress, ReadingProgress.document_id == Document.id)
            .where(Paper.user_id == user_id, ReadingProgress.user_id == user_id)
            .order_by(ReadingProgress.last_read_at.desc(), ReadingProgress.id.desc())
            .limit(limit)
        )
        return result.mappings().all()

    async def recent_papers(self, user_id: uuid.UUID, limit: int = 5):
        result = await self.db.execute(
            select(
                Paper.id, Paper.title, Paper.publication_year,
                self._first_author().label("author"), Paper.reading_status,
                Paper.created_at, Paper.updated_at,
            )
            .where(Paper.user_id == user_id)
            .order_by(Paper.created_at.desc(), Paper.id.desc())
            .limit(limit)
        )
        return result.mappings().all()

    async def recent_notes(self, user_id: uuid.UUID, limit: int = 5):
        result = await self.db.execute(
            select(
                Note.id, Note.title, Note.note_type, Note.paper_id,
                Paper.title.label("paper_title"), Note.updated_at,
            )
            .outerjoin(Paper, Paper.id == Note.paper_id)
            .where(Note.user_id == user_id)
            .order_by(Note.updated_at.desc(), Note.id.desc())
            .limit(limit)
        )
        return result.mappings().all()

    async def tags(self, user_id: uuid.UUID, since: datetime, limit: int = 20):
        result = await self.db.execute(
            select(Tag.id, Tag.name, func.count(PaperTag.paper_id).label("paper_count"))
            .join(PaperTag, PaperTag.tag_id == Tag.id)
            .join(Paper, Paper.id == PaperTag.paper_id)
            .where(Tag.user_id == user_id, Paper.user_id == user_id, Paper.created_at >= since)
            .group_by(Tag.id, Tag.name)
            .order_by(func.count(PaperTag.paper_id).desc(), Tag.name)
            .limit(limit)
        )
        return result.mappings().all()

    async def keywords(self, user_id: uuid.UUID, since: datetime, limit: int = 20):
        result = await self.db.execute(
            select(
                Keyword.id, Keyword.display_name.label("name"),
                func.count(distinct(PaperKeyword.paper_id)).label("paper_count"),
            )
            .join(PaperKeyword, PaperKeyword.keyword_id == Keyword.id)
            .join(Paper, Paper.id == PaperKeyword.paper_id)
            .where(Keyword.user_id == user_id, Paper.user_id == user_id, Paper.created_at >= since)
            .group_by(Keyword.id, Keyword.display_name)
            .order_by(func.count(distinct(PaperKeyword.paper_id)).desc(), Keyword.display_name)
            .limit(limit)
        )
        return result.mappings().all()

    async def reading_trend(self, user_id: uuid.UUID, start_date: date):
        result = await self.db.execute(
            select(
                ReadingActivity.activity_date,
                func.count(distinct(ReadingActivity.paper_id)).label("papers_read"),
                func.coalesce(func.sum(ReadingActivity.reading_time_seconds), 0).label("reading_time_seconds"),
            )
            .where(
                ReadingActivity.user_id == user_id,
                ReadingActivity.activity_date >= start_date,
            )
            .group_by(ReadingActivity.activity_date)
            .order_by(ReadingActivity.activity_date)
        )
        return result.all()
