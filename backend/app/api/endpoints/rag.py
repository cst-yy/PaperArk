import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import RAGContextError, SemanticRetrievalError
from app.schemas.rag import RAGContextRequest, RAGContextResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/context", response_model=RAGContextResponse)
async def build_rag_context(request: RAGContextRequest, db: AsyncSession = Depends(get_db),
                            user_id: uuid.UUID = Depends(get_current_user_id)):
    """Retrieve and assemble provenance-rich context without invoking an LLM."""
    try:
        return await RAGService(db).build_context(user_id, request)
    except RAGContextError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except SemanticRetrievalError as exc:
        raise HTTPException(status_code=503, detail={"message": exc.message, "detail": exc.detail}) from exc
