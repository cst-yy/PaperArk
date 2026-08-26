import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_current_user_id
from app.schemas.paper_list import (
    BatchPaperDelete, BatchPaperUpdate, PaperListPage, PaperListPreference,
    PaperListSort, SortOrder, PaperListViewSettings, PaperListViewSettingsPatch,
)
from app.services.paper_list_service import PaperListService, get_paper_list_service
from app.services.paper_service import PaperService, get_paper_service
from app.core.exceptions import InvalidFolderError, InvalidTagError, PaperNotFoundError
from app.core.exceptions import RevisionConflictError

router = APIRouter()


@router.get("/", response_model=PaperListPage)
async def list_papers(
    q: str | None = None, year_from: int | None = Query(None, ge=1000, le=9999), year_to: int | None = Query(None, ge=1000, le=9999),
    journal: str | None = None, author: str | None = None, tag_id: uuid.UUID | None = None, keyword: str | None = None,
    reading_status: Literal["unread", "reading", "finished", "archived"] | None = None, starred: bool | None = None,
    sort: PaperListSort = "updated_at", order: SortOrder = "desc", page: int = Query(1, ge=1),
    page_size: Literal["25", "50", "100", "200"] = "50",
    service: PaperListService = Depends(get_paper_list_service), user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.list_rows(user_id, q=q, year_from=year_from, year_to=year_to, journal=journal, author=author,
        tag_id=tag_id, keyword=keyword, reading_status=reading_status, starred=starred, sort=sort, order=order,
        page=page, page_size=int(page_size))


@router.get("/preference", response_model=PaperListPreference)
async def get_preference(
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.get_preference(user_id)


@router.put("/preference", response_model=PaperListPreference)
async def save_preference(
    preference: PaperListPreference,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.save_preference(user_id, preference)


@router.get("/view-settings", response_model=PaperListViewSettings)
async def get_view_settings(
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.get_view_settings(user_id)


@router.patch("/view-settings", response_model=PaperListViewSettings)
async def patch_view_settings(
    patch: PaperListViewSettingsPatch,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.patch_view_settings(user_id, patch)
    except RevisionConflictError as error:
        raise HTTPException(status_code=409, detail=error.message) from error


@router.post("/batch-update")
async def batch_update(
    data: BatchPaperUpdate,
    service: PaperListService = Depends(get_paper_list_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        count = await service.batch_update(user_id, data)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    except (InvalidTagError, InvalidFolderError) as error:
        raise HTTPException(status_code=400, detail=error.message) from error
    return {"updated": count}


@router.post("/batch-delete")
async def batch_delete(
    data: BatchPaperDelete,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        count = await service.delete_papers_atomic(user_id, data.paper_ids)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error
    return {"deleted": count}
