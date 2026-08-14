"""Application service for user-scoped reference reads."""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Reference
from app.repositories.reference_repository import ReferenceRepository


class ReferenceService:
    def __init__(self, db: AsyncSession):
        self.repo = ReferenceRepository(db)

    async def list_for_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[Reference] | None:
        return await self.repo.list_for_document(user_id, document_id)


def get_reference_service(db: AsyncSession = Depends(get_db)) -> ReferenceService:
    return ReferenceService(db)
