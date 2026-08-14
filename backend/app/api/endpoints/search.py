import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.schemas.search import SearchPageResponse
from app.services.search_service import SearchService
from app.core.exceptions import SemanticRetrievalError

router = APIRouter()


@router.get("/", response_model=SearchPageResponse)
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mode: Literal["lexical", "semantic", "hybrid"] = Query("lexical"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Search and paginate user-owned papers after aggregating all hit sources."""
    try:
        return await SearchService(db).search(user_id, q, page, page_size, mode)
    except SemanticRetrievalError as exc:
        raise HTTPException(status_code=503, detail={"message": exc.message, "detail": exc.detail}) from exc
