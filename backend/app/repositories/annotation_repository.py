"""User-scoped data access for PDF research annotations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Annotation


class AnnotationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, annotation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Annotation | None:
        result = await self.db.execute(
            select(Annotation).where(
                Annotation.id == annotation_id,
                Annotation.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def list_by_paper(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        page_number: int | None = None,
    ) -> list[Annotation]:
        stmt = select(Annotation).where(
            Annotation.user_id == user_id,
            Annotation.paper_id == paper_id,
        )
        if document_id is not None:
            stmt = stmt.where(Annotation.document_id == document_id)
        if page_number is not None:
            stmt = stmt.where(Annotation.page_number == page_number)
        stmt = stmt.order_by(Annotation.page_number, Annotation.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Annotation:
        annotation = Annotation(**kwargs)
        self.db.add(annotation)
        await self.db.flush()
        return annotation

    async def delete(self, annotation: Annotation) -> None:
        await self.db.delete(annotation)
        await self.db.flush()
