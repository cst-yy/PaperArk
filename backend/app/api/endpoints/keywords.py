import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_current_user_id
from app.core.exceptions import KeywordNotFoundError
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


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: uuid.UUID,
    service: KeywordService = Depends(get_keyword_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a user-owned keyword and all of its paper associations."""
    try:
        await service.delete_keyword(user_id, keyword_id)
    except KeywordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message) from error
