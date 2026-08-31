import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.schemas.ai_chat import *
from app.schemas.note import NoteResponse
from app.services.ai_chat_service import AIChatService
from app.services.ai_gateway import AIBudgetExceededError
from app.core.exceptions import GenerationProviderError

router=APIRouter()


@router.post("/papers/{paper_id}/chat-sessions",response_model=ChatSessionResponse,status_code=201)
async def create_session(paper_id:uuid.UUID,data:ChatSessionCreate,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:return await AIChatService(db).create_session(user_id,paper_id,data)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc


@router.get("/papers/{paper_id}/chat-sessions",response_model=list[ChatSessionResponse])
async def sessions(paper_id:uuid.UUID,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:return await AIChatService(db).sessions(user_id,paper_id)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc


@router.get("/chat-sessions/{session_id}",response_model=ChatSessionResponse)
async def session(session_id:uuid.UUID,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:return await AIChatService(db).session(user_id,session_id)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc


@router.patch("/chat-sessions/{session_id}",response_model=ChatSessionResponse)
async def rename(session_id:uuid.UUID,data:ChatSessionUpdate,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:row=await AIChatService(db).update_session(user_id,session_id,data)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc
    return row


@router.delete("/chat-sessions/{session_id}",status_code=204)
async def delete(session_id:uuid.UUID,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:row=await AIChatService(db).session(user_id,session_id)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc
    await db.delete(row);return Response(status_code=204)


@router.get("/chat-sessions/{session_id}/messages",response_model=list[ChatMessageResponse])
async def messages(session_id:uuid.UUID,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:return await AIChatService(db).messages(user_id,session_id)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc


@router.post("/chat-sessions/{session_id}/messages",response_model=ChatTurnResponse)
async def ask(session_id:uuid.UUID,data:ChatMessageCreate,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:
        user,assistant=await AIChatService(db).ask(user_id,session_id,data)
        return ChatTurnResponse(user_message=user,assistant_message=assistant)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc
    except PermissionError as exc:raise HTTPException(403,detail=str(exc)) from exc
    except AIBudgetExceededError as exc:raise HTTPException(402,detail=str(exc)) from exc
    except GenerationProviderError as exc:raise HTTPException(503,detail="AI Provider 暂时无响应，请稍后重试") from exc
    except ValueError as exc:raise HTTPException(422,detail=str(exc)) from exc


@router.post("/chat-messages/{message_id}/save-as-note",response_model=NoteResponse,status_code=201)
async def save(message_id:uuid.UUID,db:AsyncSession=Depends(get_db),user_id:uuid.UUID=Depends(get_current_user_id)):
    try:return await AIChatService(db).save_as_note(user_id,message_id)
    except LookupError as exc:raise HTTPException(404,detail=str(exc)) from exc
