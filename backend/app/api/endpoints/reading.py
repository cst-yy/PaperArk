"""Reading API endpoints — aggregate user reading state."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.schemas.reading_progress import RecentReadingItem
from app.services.reading_progress_service import ReadingProgressService

router = APIRouter()


@router.get("/recent", response_model=list[RecentReadingItem])
async def list_recent_reading(
    limit: int = Query(5, ge=1, le=20),
    mine: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List the current user's recently persisted concrete PDF reading positions."""
    return await ReadingProgressService(db).list_recent_reading(user_id, limit=limit, mine=mine)
