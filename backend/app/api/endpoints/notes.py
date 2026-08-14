import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DEFAULT_USER_ID, get_db
from app.models import Note
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate

router = APIRouter()


@router.get("/", response_model=list[NoteResponse])
async def list_notes(
    paper_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Note).where(Note.user_id == DEFAULT_USER_ID)
    if paper_id:
        stmt = stmt.where(Note.paper_id == paper_id)
    stmt = stmt.order_by(Note.updated_at.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=NoteResponse)
async def create_note(data: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = Note(
        user_id=DEFAULT_USER_ID,
        paper_id=data.paper_id,
        title=data.title,
        content=data.content,
    )
    db.add(note)
    await db.flush()
    return note


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID, data: NoteUpdate, db: AsyncSession = Depends(get_db)
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)

    await db.flush()
    return note


@router.delete("/{note_id}")
async def delete_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    return {"message": "Note deleted"}
