import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_current_user_id
from app.core.exceptions import DuplicateTagError, PaperNotFoundError, TagNotFoundError
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.services.paper_service import PaperService, get_paper_service
from app.services.tag_service import TagService, get_tag_service

router = APIRouter()


def _handle_tag_error(error: Exception) -> None:
    if isinstance(error, TagNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message) from error
    if isinstance(error, DuplicateTagError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.message) from error
    if isinstance(error, PaperNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message) from error
    raise error


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    service: TagService = Depends(get_tag_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.list_tags(user_id)


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: TagCreate,
    service: TagService = Depends(get_tag_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.create_tag(user_id, data)
    except (DuplicateTagError, TagNotFoundError) as error:
        _handle_tag_error(error)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    service: TagService = Depends(get_tag_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.update_tag(user_id, tag_id, data)
    except (DuplicateTagError, TagNotFoundError) as error:
        _handle_tag_error(error)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    service: TagService = Depends(get_tag_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        await service.delete_tag(user_id, tag_id)
    except TagNotFoundError as error:
        _handle_tag_error(error)


@router.post("/{tag_id}/papers/{paper_id}")
async def add_tag_to_paper(
    tag_id: uuid.UUID,
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        await service.add_tag(user_id, paper_id, tag_id)
    except (PaperNotFoundError, TagNotFoundError) as error:
        _handle_tag_error(error)
    return {"message": "Tag added"}


@router.delete("/{tag_id}/papers/{paper_id}")
async def remove_tag_from_paper(
    tag_id: uuid.UUID,
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        await service.remove_tag(user_id, paper_id, tag_id)
    except (PaperNotFoundError, TagNotFoundError) as error:
        _handle_tag_error(error)
    return {"message": "Tag removed"}
