import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import PaperNotFoundError, RevisionConflictError, TodoNotFoundError
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate
from app.services.todo_service import TodoService

router = APIRouter()

def fail(error: Exception):
    if isinstance(error, RevisionConflictError): raise HTTPException(409, str(error))
    if isinstance(error, (TodoNotFoundError, PaperNotFoundError)): raise HTTPException(404, str(error))
    raise error

@router.get("/", response_model=list[TodoResponse])
async def list_todos(completed: bool = False, limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await TodoService(db).list(user_id, completed, limit)

@router.post("/", response_model=TodoResponse, status_code=201)
async def create_todo(data: TodoCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await TodoService(db).create(user_id, data)
    except Exception as error: fail(error)

@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: uuid.UUID, data: TodoUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await TodoService(db).update(user_id, todo_id, data)
    except Exception as error: fail(error)

@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: await TodoService(db).delete(user_id, todo_id); return Response(status_code=204)
    except Exception as error: fail(error)
