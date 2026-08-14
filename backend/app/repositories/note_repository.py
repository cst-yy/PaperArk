"""Note repository - data access for notes and note links."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, NoteLink


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> Note | None:
        stmt = select(Note).where(
            Note.user_id == user_id,
            Note.paper_id == paper_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, note_id: uuid.UUID) -> Note | None:
        return await self.db.get(Note, note_id)

    async def create(self, user_id: uuid.UUID, paper_id: uuid.UUID, **kwargs) -> Note:
        note = Note(user_id=user_id, paper_id=paper_id, **kwargs)
        self.db.add(note)
        await self.db.flush()
        return note

    async def update(self, note_id: uuid.UUID, **kwargs) -> Note | None:
        note = await self.db.get(Note, note_id)
        if note:
            for key, value in kwargs.items():
                setattr(note, key, value)
            await self.db.flush()
        return note

    async def delete(self, note_id: uuid.UUID) -> bool:
        note = await self.db.get(Note, note_id)
        if note:
            await self.db.delete(note)
            return True
        return False

    async def list_recent(self, user_id: uuid.UUID, limit: int = 10) -> list[Note]:
        stmt = (
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_links(self, note_id: uuid.UUID) -> list[NoteLink]:
        stmt = select(NoteLink).where(
            (NoteLink.source_note_id == note_id) | (NoteLink.target_note_id == note_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
