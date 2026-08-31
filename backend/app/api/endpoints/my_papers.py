import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.models import ResearchIdentity
from app.schemas.paper import PaperPageResponse, ReadingStatus
from app.schemas.reading_progress import RecentReadingItem
from app.services.paper_service import PaperService
from app.services.reading_progress_service import ReadingProgressService

router = APIRouter()


@router.get("", response_model=PaperPageResponse)
async def list_my_papers(
    q: str | None = None,
    authorship: Literal["all", "first", "corresponding", "other"] = "all",
    year: int | None = None,
    reading_status: ReadingStatus | None = None,
    title_query: str | None = Query(None, max_length=500),
    author_query: str | None = Query(None, max_length=200),
    abstract_query: str | None = Query(None, max_length=500),
    venue_query: str | None = Query(None, max_length=200),
    keyword_query: str | None = Query(None, max_length=200),
    tag_query: str | None = Query(None, max_length=200),
    identifier_query: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id),
):
    identity = await db.scalar(select(ResearchIdentity).where(ResearchIdentity.user_id == user_id))
    if identity is None: return PaperPageResponse(items=[], page=page, page_size=page_size, total=0, total_pages=0)
    return await PaperService(db).list_papers(user_id=user_id, q=q, year=year,
        reading_status=reading_status, title_query=title_query,
        author_query=author_query, abstract_query=abstract_query,
        venue_query=venue_query, keyword_query=keyword_query,
        tag_query=tag_query, identifier_query=identifier_query,
        identity_author_id=identity.author_id,
        author_role=None if authorship == "all" else authorship, page=page, page_size=page_size)


@router.get("/recent-reading", response_model=list[RecentReadingItem])
async def recent_reading(limit: int = Query(4, ge=1, le=10), db: AsyncSession = Depends(get_db),
                         user_id: uuid.UUID = Depends(get_current_user_id)):
    return await ReadingProgressService(db).list_recent_reading(user_id, limit=limit, mine=True)
