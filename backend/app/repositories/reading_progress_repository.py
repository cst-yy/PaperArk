"""Data access for document-scoped reading progress."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, Paper, PaperAuthor, ReadingActivity, ReadingProgress


class ReadingProgressRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> ReadingProgress | None:
        result = await self.db.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.document_id == document_id,
            )
        )
        return result.scalars().first()

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        current_page: int,
        total_pages: int,
        progress_ratio: float,
        reading_time_seconds_delta: int,
    ) -> ReadingProgress:
        statement = insert(ReadingProgress).values(
            user_id=user_id,
            document_id=document_id,
            current_page=current_page,
            total_pages=total_pages,
            progress_ratio=progress_ratio,
            reading_time_seconds=reading_time_seconds_delta,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_reading_progress_user_document",
            set_={
                "current_page": statement.excluded.current_page,
                "total_pages": statement.excluded.total_pages,
                "progress_ratio": statement.excluded.progress_ratio,
                "last_read_at": func.now(),
                "reading_time_seconds": ReadingProgress.reading_time_seconds + statement.excluded.reading_time_seconds,
            },
        ).returning(ReadingProgress)
        result = await self.db.execute(statement)
        return result.scalar_one()

    async def upsert_daily_activity(
        self, *, user_id: uuid.UUID, paper_id: uuid.UUID, document_id: uuid.UUID,
        reading_time_seconds_delta: int,
    ) -> None:
        statement = insert(ReadingActivity).values(
            user_id=user_id,
            paper_id=paper_id,
            document_id=document_id,
            activity_date=func.current_date(),
            reading_time_seconds=reading_time_seconds_delta,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_reading_activity_user_document_date",
            set_={
                "last_read_at": func.now(),
                "updated_at": func.now(),
                "reading_time_seconds": ReadingActivity.reading_time_seconds + statement.excluded.reading_time_seconds,
            },
        )
        await self.db.execute(statement)

    async def list_recent(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[tuple[ReadingProgress, Paper]]:
        """Return concrete PDF reading records, newest first, with safe paper scope."""
        statement = (
            select(ReadingProgress, Paper)
            .join(Document, Document.id == ReadingProgress.document_id)
            .join(Paper, Paper.id == Document.paper_id)
            .where(
                ReadingProgress.user_id == user_id,
                Paper.user_id == user_id,
            )
            .options(
                selectinload(Paper.authors).selectinload(PaperAuthor.author),
            )
            .order_by(ReadingProgress.last_read_at.desc(), ReadingProgress.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return list(result.all())
