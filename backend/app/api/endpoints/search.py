import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.services.search_service import SearchService

router = APIRouter()


class SearchResult(BaseModel):
    paper_id: str
    title: str
    snippet: str
    page_number: int | None = None
    section_title: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Full-text search across user-scoped paper metadata and PDF chunks."""
    service = SearchService(db)
    results = await service.full_text_search(user_id, q, limit)
    return SearchResponse(
        query=q,
        results=[SearchResult(**result) for result in results],
        total=len(results),
    )
