import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import InvalidNoteError, NoteNotFoundError
from app.schemas.note import NoteAggregateSave, NoteCreate, NoteEvidenceReplacement, NoteResponse, NoteUpdate
from app.services.note_service import NoteService
from app.schemas.research_note import ResearchProfileAggregate, ResearchProfileResponse
from app.services.research_note_service import ResearchNoteService

router = APIRouter()

@router.get("/{note_id}/research-profile", response_model=ResearchProfileResponse | None)
async def get_research_profile(note_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await ResearchNoteService(db).get(user_id, note_id)
    except (NoteNotFoundError, InvalidNoteError) as error: raise _http_error(error)

@router.put("/{note_id}/research-profile", response_model=ResearchProfileResponse)
async def save_research_profile(note_id: uuid.UUID, data: ResearchProfileAggregate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await ResearchNoteService(db).save(user_id, note_id, data)
    except (NoteNotFoundError, InvalidNoteError) as error: raise _http_error(error)


def _http_error(error: Exception) -> HTTPException:
    return HTTPException(status_code=404 if isinstance(error, NoteNotFoundError) else 400, detail=str(error))


@router.get("/", response_model=list[NoteResponse])
async def list_notes(paper_id: uuid.UUID | None = Query(None), db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).list_notes(user_id, paper_id)
    except InvalidNoteError as error:
        raise _http_error(error)


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(data: NoteCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).create_note(user_id, data)
    except InvalidNoteError as error:
        raise _http_error(error)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).get_note(user_id, note_id)
    except NoteNotFoundError as error:
        raise _http_error(error)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: uuid.UUID, data: NoteUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).update_note(user_id, note_id, data)
    except (NoteNotFoundError, InvalidNoteError) as error:
        raise _http_error(error)


@router.put("/{note_id}", response_model=NoteResponse)
async def save_note_aggregate(note_id: uuid.UUID, data: NoteAggregateSave, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).save_aggregate(user_id, note_id, data)
    except (NoteNotFoundError, InvalidNoteError) as error:
        raise _http_error(error)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)) -> Response:
    try:
        await NoteService(db).delete_note(user_id, note_id)
    except NoteNotFoundError as error:
        raise _http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{note_id}/evidence", response_model=NoteResponse)
async def replace_note_evidence(note_id: uuid.UUID, data: NoteEvidenceReplacement, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).replace_evidence(user_id, note_id, data.annotation_ids)
    except (NoteNotFoundError, InvalidNoteError) as error:
        raise _http_error(error)


@router.post("/{note_id}/evidence/{annotation_id}", response_model=NoteResponse)
async def attach_note_evidence(note_id: uuid.UUID, annotation_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).attach_evidence(user_id, note_id, annotation_id)
    except (NoteNotFoundError, InvalidNoteError) as error:
        raise _http_error(error)


@router.delete("/{note_id}/evidence/{annotation_id}", response_model=NoteResponse)
async def detach_note_evidence(note_id: uuid.UUID, annotation_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        return await NoteService(db).detach_evidence(user_id, note_id, annotation_id)
    except (NoteNotFoundError, InvalidNoteError) as error:
        raise _http_error(error)
