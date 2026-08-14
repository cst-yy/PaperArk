"""Application service for the S9-A Markdown Note aggregate."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidNoteError, NoteNotFoundError
from app.models import Annotation, Note, NoteEvidence, Paper
from app.repositories.note_evidence_repository import NoteEvidenceRepository
from app.repositories.note_repository import NoteRepository
from app.schemas.note import NoteAggregateSave, NoteCreate, NoteUpdate


class NoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = NoteRepository(db)
        self.evidence_repository = NoteEvidenceRepository(db)

    async def _validate_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID | None) -> None:
        if paper_id is None:
            return
        owned = await self.db.scalar(select(Paper.id).where(Paper.id == paper_id, Paper.user_id == user_id))
        if owned is None:
            raise InvalidNoteError("Paper does not exist or belongs to another user")

    async def list_notes(self, user_id: uuid.UUID, paper_id: uuid.UUID | None = None) -> list[Note]:
        if paper_id is not None:
            await self._validate_paper(user_id, paper_id)
        return await self.repository.list(user_id, paper_id)

    async def get_note(self, user_id: uuid.UUID, note_id: uuid.UUID) -> Note:
        note = await self.repository.get(user_id, note_id)
        if note is None:
            raise NoteNotFoundError("Note not found")
        return note

    async def create_note(self, user_id: uuid.UUID, data: NoteCreate) -> Note:
        await self._validate_paper(user_id, data.paper_id)
        annotations = await self._validate_annotations(user_id, data.paper_id, data.annotation_ids)
        note = Note(user_id=user_id, **data.model_dump(exclude={"annotation_ids"}))
        await self.repository.create(note)
        if annotations:
            await self._write_evidence(note, data.annotation_ids, annotations)
        return await self.get_note(user_id, note.id)

    async def update_note(self, user_id: uuid.UUID, note_id: uuid.UUID, data: NoteUpdate) -> Note:
        note = await self.get_note(user_id, note_id)
        changes = data.model_dump(exclude_unset=True)
        paper_id = changes.get("paper_id", note.paper_id)
        note_type = changes.get("note_type", note.note_type)
        if note_type != note.note_type:
            raise InvalidNoteError("note_type is immutable after creation")
        if note_type in {"paper", "research"} and paper_id is None:
            raise InvalidNoteError("paper and research notes require paper_id")
        if "paper_id" in changes:
            await self._validate_paper(user_id, paper_id)
        embedding_changed = any(field in changes and changes[field] != getattr(note, field) for field in ("title", "content_markdown"))
        for field, value in changes.items():
            setattr(note, field, value)
        if embedding_changed:
            note.embedding_status = "pending"
            note.embedding_error = None
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def save_aggregate(self, user_id: uuid.UUID, note_id: uuid.UUID, data: NoteAggregateSave) -> Note:
        note = await self.get_note(user_id, note_id)
        if data.note_type != note.note_type:
            raise InvalidNoteError("note_type is immutable after creation")
        await self._validate_paper(user_id, data.paper_id)
        embedding_changed = data.title != note.title or data.content_markdown != note.content_markdown
        for field, value in data.model_dump().items():
            setattr(note, field, value)
        if embedding_changed:
            note.embedding_status = "pending"
            note.embedding_error = None
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def delete_note(self, user_id: uuid.UUID, note_id: uuid.UUID) -> None:
        note = await self.get_note(user_id, note_id)
        await self.repository.delete(note)

    async def replace_evidence(self, user_id: uuid.UUID, note_id: uuid.UUID, annotation_ids: list[uuid.UUID]) -> Note:
        note = await self.get_note(user_id, note_id)
        if len(set(annotation_ids)) != len(annotation_ids):
            raise InvalidNoteError("annotation_ids must be unique")
        annotations = await self._validate_annotations(user_id, note.paper_id, annotation_ids)
        await self._write_evidence(note, annotation_ids, annotations)
        return await self.get_note(user_id, note.id)

    async def attach_evidence(self, user_id: uuid.UUID, note_id: uuid.UUID, annotation_id: uuid.UUID) -> Note:
        note = await self.get_note(user_id, note_id)
        current = [item.annotation_id for item in note.evidence]
        if annotation_id not in current:
            current.append(annotation_id)
        return await self.replace_evidence(user_id, note_id, current)

    async def detach_evidence(self, user_id: uuid.UUID, note_id: uuid.UUID, annotation_id: uuid.UUID) -> Note:
        note = await self.get_note(user_id, note_id)
        current = [item.annotation_id for item in note.evidence if item.annotation_id != annotation_id]
        return await self.replace_evidence(user_id, note_id, current)

    async def _validate_annotations(self, user_id: uuid.UUID, paper_id: uuid.UUID | None, annotation_ids: list[uuid.UUID]) -> list[Annotation]:
        if len(set(annotation_ids)) != len(annotation_ids):
            raise InvalidNoteError("annotation_ids must be unique")
        annotations = await self.evidence_repository.get_annotations(user_id, annotation_ids)
        by_id = {annotation.id: annotation for annotation in annotations}
        if len(by_id) != len(annotation_ids):
            raise InvalidNoteError("One or more annotations do not exist or belong to another user")
        ordered = [by_id[annotation_id] for annotation_id in annotation_ids]
        if paper_id is not None and any(annotation.paper_id != paper_id for annotation in ordered):
            raise InvalidNoteError("Paper notes may only reference annotations from the same paper")
        return ordered

    async def _write_evidence(self, note: Note, annotation_ids: list[uuid.UUID], annotations: list[Annotation]) -> None:
        snapshots = await self.evidence_repository.existing_snapshots(note.id)
        rows = [NoteEvidence(
            note_id=note.id,
            annotation_id=annotation.id,
            order_index=index,
            quote_snapshot=snapshots.get(annotation.id) or self._quote_snapshot(annotation),
        ) for index, annotation in enumerate(annotations)]
        await self.evidence_repository.replace(note.id, rows)
        self.db.expire(note, ["evidence"])

    @staticmethod
    def _quote_snapshot(annotation: Annotation) -> str:
        return (annotation.selected_text or annotation.comment or annotation.content
            or f"[Area annotation on page {annotation.page_number}]")
