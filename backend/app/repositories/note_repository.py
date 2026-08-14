"""User-scoped persistence for Markdown notes."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, user_id: uuid.UUID, paper_id: uuid.UUID | None = None) -> list[Note]:
        statement = select(Note).where(Note.user_id == user_id)
        if paper_id is not None:
            statement = statement.where(Note.paper_id == paper_id)
        result = await self.db.execute(statement.order_by(Note.updated_at.desc(), Note.id))
        return list(result.scalars().all())

    async def get(self, user_id: uuid.UUID, note_id: uuid.UUID) -> Note | None:
        result = await self.db.execute(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, note: Note) -> Note:
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def delete(self, note: Note) -> None:
        await self.db.delete(note)
        await self.db.flush()
