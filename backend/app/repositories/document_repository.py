"""Document repository — data access layer for documents.

All queries are user-scoped via a JOIN to Paper.user_id.
A user can never access another user's documents even if they know the UUID.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Document | None:
        """Get a single document, scoped to user_id via Paper join."""
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.id == document_id, Paper.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_paper(
        self, paper_id: uuid.UUID, user_id: uuid.UUID
    ) -> Document | None:
        """Get the primary document for a paper, scoped to user_id."""
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.paper_id == paper_id, Paper.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_paper(
        self, paper_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Document]:
        """List every document for a paper, scoped to its owning user."""
        stmt = (
            select(Document)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Document.paper_id == paper_id, Paper.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Document:
        doc = Document(**kwargs)
        self.db.add(doc)
        await self.db.flush()
        return doc
