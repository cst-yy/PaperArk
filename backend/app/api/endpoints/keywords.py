import uuid

from fastapi import APIRouter, Depends

from app.core.database import get_current_user_id
from app.schemas.keyword import KeywordResponse
from app.services.keyword_service import KeywordService, get_keyword_service

router = APIRouter()


@router.get("/", response_model=list[KeywordResponse])
async def list_keywords(
    service: KeywordService = Depends(get_keyword_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List the current user's academic keyword vocabulary for autocomplete."""
    return await service.list_keywords(user_id)
