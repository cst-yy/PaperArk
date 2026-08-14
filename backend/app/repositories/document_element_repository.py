"""User-scoped queries for PDF-derived document elements."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentElement, Paper


class DocumentElementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID, element_type: str | None = None
    ) -> list[DocumentElement] | None:
        ownership = (
            select(Document.id)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.id == document_id, Paper.user_id == user_id)
        )
        if not (await self.db.execute(ownership)).scalar_one_or_none():
            return None
        stmt = select(DocumentElement).where(DocumentElement.document_id == document_id)
        if element_type:
            stmt = stmt.where(DocumentElement.element_type == element_type)
        stmt = stmt.order_by(DocumentElement.order_index)
        return list((await self.db.execute(stmt)).scalars().all())
