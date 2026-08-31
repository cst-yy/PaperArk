"""Business rules for document-scoped reading progress."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import DocumentNotFoundError, PaperNotFoundError
from app.models import Document, Paper, ReadingProgress, ResearchIdentity
from app.repositories.paper_repository import PaperRepository
from app.repositories.reading_progress_repository import ReadingProgressRepository
from app.schemas.reading_progress import (
    ReadingProgressResponse,
    ReadingProgressUpsert,
    RecentReadingDocument,
    RecentReadingItem,
    RecentReadingPaper,
)


class ReadingProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReadingProgressRepository(db)
        self.paper_repo = PaperRepository(db)

    async def get_progress(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, document_id: uuid.UUID
    ) -> ReadingProgressResponse | None:
        await self._get_owned_document(user_id, paper_id, document_id)
        progress = await self.repo.get_by_document(user_id, document_id)
        return self._to_response(paper_id, progress) if progress else None

    async def upsert_progress(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        data: ReadingProgressUpsert,
    ) -> ReadingProgressResponse:
        await self._get_owned_document(user_id, paper_id, data.document_id)
        progress = await self.repo.upsert(
            user_id=user_id,
            document_id=data.document_id,
            current_page=data.current_page,
            total_pages=data.total_pages,
            progress_ratio=data.current_page / data.total_pages,
            reading_time_seconds_delta=data.reading_time_seconds_delta,
        )
        await self.repo.upsert_daily_activity(
            user_id=user_id, paper_id=paper_id, document_id=data.document_id,
            reading_time_seconds_delta=data.reading_time_seconds_delta,
        )
        # This automatic transition is intentionally conditional: concurrent or
        # delayed progress writes cannot overwrite finished/archived choices.
        await self.paper_repo.mark_reading_if_unread(user_id, paper_id)
        await self.db.flush()
        return self._to_response(paper_id, progress)

    async def list_recent_reading(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        mine: bool = False,
    ) -> list[RecentReadingItem]:
        identity_author_id = None
        if mine:
            identity = await self.db.scalar(select(ResearchIdentity).where(ResearchIdentity.user_id == user_id))
            if identity is None: return []
            identity_author_id = identity.author_id
        records = await self.repo.list_recent(user_id, limit=limit, identity_author_id=identity_author_id)
        return [self._to_recent_item(progress, paper, identity_author_id) for progress, paper in records]

    async def _get_owned_document(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        paper = await self.db.scalar(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        document = await self.db.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.paper_id == paper_id,
            )
        )
        if not document:
            raise DocumentNotFoundError(
                f"Document {document_id} does not belong to paper {paper_id}"
            )
        return document

    @staticmethod
    def _to_response(
        paper_id: uuid.UUID, progress: ReadingProgress
    ) -> ReadingProgressResponse:
        return ReadingProgressResponse(
            paper_id=paper_id,
            document_id=progress.document_id,
            current_page=progress.current_page,
            total_pages=progress.total_pages,
            progress_ratio=progress.progress_ratio,
            last_read_at=progress.last_read_at,
            reading_time_seconds=progress.reading_time_seconds,
        )

    @staticmethod
    def _to_recent_item(
        progress: ReadingProgress,
        paper: Paper,
        identity_author_id: uuid.UUID | None = None,
    ) -> RecentReadingItem:
        authors = sorted(paper.authors, key=lambda assignment: assignment.author_order)
        identity_link = next((link for link in authors if link.author_id == identity_author_id), None)
        return RecentReadingItem(
            paper=RecentReadingPaper(
                id=paper.id,
                title=paper.title,
                publication_year=paper.publication_year,
                authors=[assignment.author.name for assignment in authors],
                is_starred=paper.is_starred,
                my_author_roles={
                    "author_order": identity_link.author_order,
                    "is_first_author": identity_link.author_order == 0,
                    "is_co_first": identity_link.is_co_first,
                    "is_corresponding": identity_link.is_corresponding,
                } if identity_link else None,
            ),
            document=RecentReadingDocument(id=progress.document_id),
            current_page=progress.current_page,
            total_pages=progress.total_pages,
            progress_ratio=progress.progress_ratio,
            last_read_at=progress.last_read_at,
        )
