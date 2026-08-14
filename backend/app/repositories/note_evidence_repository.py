"""Persistence primitives for ordered NoteEvidence replacement."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Annotation, NoteEvidence


class NoteEvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_annotations(self, user_id: uuid.UUID, annotation_ids: list[uuid.UUID]) -> list[Annotation]:
        if not annotation_ids:
            return []
        result = await self.db.execute(select(Annotation).where(
            Annotation.user_id == user_id, Annotation.id.in_(annotation_ids)
        ))
        return list(result.scalars().all())

    async def existing_snapshots(self, note_id: uuid.UUID) -> dict[uuid.UUID, str | None]:
        rows = (await self.db.execute(select(
            NoteEvidence.annotation_id, NoteEvidence.quote_snapshot
        ).where(NoteEvidence.note_id == note_id))).all()
        return dict(rows)

    async def replace(self, note_id: uuid.UUID, rows: list[NoteEvidence]) -> None:
        await self.db.execute(delete(NoteEvidence).where(NoteEvidence.note_id == note_id))
        await self.db.flush()
        self.db.add_all(rows)
        await self.db.flush()
