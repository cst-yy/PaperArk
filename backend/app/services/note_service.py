"""Note service - CRUD for markdown notes and note links."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, NoteLink


class NoteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> Note:
        stmt = select(Note).where(
            Note.user_id == user_id,
            Note.paper_id == paper_id,
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            note = Note(user_id=user_id, paper_id=paper_id, content="")
            self.db.add(note)
            await self.db.flush()

        return note

    async def update_content(
        self, note_id: uuid.UUID, content: str, title: str | None = None
    ) -> Note | None:
        note = await self.db.get(Note, note_id)
        if note:
            note.content = content
            if title is not None:
                note.title = title
            await self.db.flush()
        return note

    async def create_link(
        self, source_id: uuid.UUID, target_id: uuid.UUID, link_text: str | None = None
    ) -> NoteLink:
        link = NoteLink(
            source_note_id=source_id,
            target_note_id=target_id,
            link_text=link_text,
        )
        self.db.add(link)
        await self.db.flush()
        return link

    async def list_recent(self, user_id: uuid.UUID, limit: int = 10) -> list[Note]:
        stmt = (
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
