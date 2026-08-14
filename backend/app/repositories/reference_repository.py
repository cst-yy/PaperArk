"""User-scoped data access for PDF-derived bibliography entries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper, Reference


class ReferenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[Reference] | None:
        """Return ``None`` when the document is not owned by this user."""
        owned_document = (
            select(Document.id)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.id == document_id, Paper.user_id == user_id)
        )
        if not (await self.db.execute(owned_document)).scalar_one_or_none():
            return None
        stmt = (
            select(Reference)
            .where(Reference.document_id == document_id)
            .options(selectinload(Reference.matched_paper))
            .order_by(Reference.order_index)
        )
        return list((await self.db.execute(stmt)).scalars().all())
