import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.schemas.search import SearchPageResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.get("/", response_model=SearchPageResponse)
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Search and paginate user-owned papers after aggregating all hit sources."""
    return await SearchService(db).search(user_id, q, page, page_size)
