"""Business orchestration for user-scoped PDF research annotations."""

import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AnnotationNotFoundError, InvalidAnnotationError, PaperNotFoundError
from app.models import Document, Paper
from app.repositories.annotation_repository import AnnotationRepository


class AnnotationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnnotationRepository(db)

    async def list_by_paper(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        page_number: int | None = None,
    ):
        paper = await self._get_owned_paper(user_id, paper_id)
        if document_id is not None:
            document = await self.db.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.paper_id == paper.id,
                )
            )
            if not document:
                raise InvalidAnnotationError("Document does not belong to the requested paper")
        return await self.repo.list_by_paper(user_id, paper_id, document_id, page_number)

    async def create(self, user_id: uuid.UUID, **kwargs):
        paper_id = kwargs["paper_id"]
        document_id = kwargs["document_id"]
        paper = await self._get_owned_paper(user_id, paper_id)
        document_result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.paper_id == paper.id,
            )
        )
        if not document_result.scalars().first():
            raise InvalidAnnotationError("Document does not belong to the requested paper")

        self._validate_normalized_position(kwargs.get("position_data"), kwargs["type"])
        comment = kwargs.pop("comment", None)
        kwargs["content"] = kwargs.get("content") or comment
        return await self.repo.create(user_id=user_id, comment=comment, **kwargs)

    async def update(self, user_id: uuid.UUID, annotation_id: uuid.UUID, **kwargs):
        annotation = await self.repo.get_by_id(annotation_id, user_id)
        if not annotation:
            raise AnnotationNotFoundError(f"Annotation {annotation_id} not found")
        if "comment" in kwargs:
            annotation.content = kwargs["comment"]
        for key, value in kwargs.items():
            setattr(annotation, key, value)
        await self.db.flush()
        return annotation

    async def delete(self, user_id: uuid.UUID, annotation_id: uuid.UUID) -> None:
        annotation = await self.repo.get_by_id(annotation_id, user_id)
        if not annotation:
            raise AnnotationNotFoundError(f"Annotation {annotation_id} not found")
        await self.repo.delete(annotation)

    async def _get_owned_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> Paper:
        result = await self.db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        paper = result.scalars().first()
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        return paper

    @staticmethod
    def _validate_normalized_position(position_data: dict | None, annotation_type: str) -> None:
        if annotation_type == "area":
            rect = (position_data or {}).get("rect")
            if (position_data or {}).get("kind") != "area" or not _is_normalized_rect(rect):
                raise InvalidAnnotationError("Area annotation requires a normalized rect")
        elif annotation_type in {"highlight", "underline"}:
            rects = (position_data or {}).get("rects")
            if (position_data or {}).get("kind") != "text" or not rects or not all(_is_normalized_rect(rect) for rect in rects):
                raise InvalidAnnotationError("Text annotation requires normalized rects")


def _is_normalized_rect(rect: object) -> bool:
    if not isinstance(rect, dict):
        return False
    values = [rect.get(key) for key in ("x", "y", "width", "height")]
    return all(isinstance(value, (int, float)) for value in values) and all(
        0 <= value <= 1 for value in values
    ) and values[2] > 0 and values[3] > 0 and values[0] + values[2] <= 1 and values[1] + values[3] <= 1


def get_annotation_service(db: AsyncSession = Depends(get_db)) -> AnnotationService:
    return AnnotationService(db)
