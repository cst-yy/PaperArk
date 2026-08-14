from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NoteCreate(BaseModel):
    paper_id: UUID
    title: str | None = None
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteResponse(ORMModel):
    id: UUID
    paper_id: UUID
    title: str | None = None
    content: str
    created_at: datetime
    updated_at: datetime


class NoteLinkCreate(BaseModel):
    source_note_id: UUID
    target_note_id: UUID
    link_text: str | None = None


class NoteLinkResponse(ORMModel):
    id: UUID
    source_note_id: UUID
    target_note_id: UUID
    link_text: str | None = None
