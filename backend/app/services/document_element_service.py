"""Application service for user-scoped DocumentElement reads."""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import DocumentElement
from app.repositories.document_element_repository import DocumentElementRepository


class DocumentElementService:
    def __init__(self, db: AsyncSession):
        self.repo = DocumentElementRepository(db)

    async def list_for_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID, element_type: str | None = None
    ) -> list[DocumentElement] | None:
        return await self.repo.list_for_document(user_id, document_id, element_type)


def get_document_element_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentElementService:
    return DocumentElementService(db)
