import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import MemoNotFoundError, PaperNotFoundError, RevisionConflictError
from app.schemas.memo import MemoCreate, MemoResponse, MemoUpdate
from app.services.memo_service import MemoService

router = APIRouter()

def fail(error: Exception):
    if isinstance(error, RevisionConflictError): raise HTTPException(409, str(error))
    if isinstance(error, (MemoNotFoundError, PaperNotFoundError)): raise HTTPException(404, str(error))
    raise error

@router.get("/", response_model=list[MemoResponse])
async def list_memos(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await MemoService(db).list(user_id, limit)

@router.post("/", response_model=MemoResponse, status_code=201)
async def create_memo(data: MemoCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await MemoService(db).create(user_id, data)
    except Exception as error: fail(error)

@router.patch("/{memo_id}", response_model=MemoResponse)
async def update_memo(memo_id: uuid.UUID, data: MemoUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await MemoService(db).update(user_id, memo_id, data)
    except Exception as error: fail(error)

@router.delete("/{memo_id}", status_code=204)
async def delete_memo(memo_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: await MemoService(db).delete(user_id, memo_id); return Response(status_code=204)
    except Exception as error: fail(error)
