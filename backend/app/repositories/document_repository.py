"""User-scoped persistence helpers for Document parsing."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, document_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.id == document_id, Paper.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_paper(self, paper_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.paper_id == paper_id, Paper.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_paper(self, paper_id: uuid.UUID, user_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.paper_id == paper_id, Paper.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Document:
        document = Document(**kwargs)
        self.db.add(document)
        await self.db.flush()
        return document
