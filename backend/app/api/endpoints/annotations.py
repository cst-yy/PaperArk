import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_current_user_id
from app.core.exceptions import AnnotationNotFoundError, DomainError, InvalidAnnotationError, PaperNotFoundError
from app.schemas.annotation import AnnotationCreate, AnnotationResponse, AnnotationUpdate
from app.services.annotation_service import AnnotationService, get_annotation_service

router = APIRouter()


def _handle_domain_error(error: DomainError) -> None:
    if isinstance(error, (AnnotationNotFoundError, PaperNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message) from error
    if isinstance(error, InvalidAnnotationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.message) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message) from error


@router.get("/", response_model=list[AnnotationResponse])
async def list_annotations(
    paper_id: uuid.UUID = Query(...),
    document_id: uuid.UUID | None = Query(None),
    page_number: int | None = Query(None, ge=1),
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnnotationService = Depends(get_annotation_service),
):
    try:
        return await service.list_by_paper(user_id, paper_id, document_id, page_number)
    except DomainError as error:
        _handle_domain_error(error)


@router.post("/", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    data: AnnotationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnnotationService = Depends(get_annotation_service),
):
    try:
        return await service.create(user_id, **data.model_dump())
    except DomainError as error:
        _handle_domain_error(error)


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: uuid.UUID,
    data: AnnotationUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnnotationService = Depends(get_annotation_service),
):
    try:
        return await service.update(
            user_id,
            annotation_id,
            **data.model_dump(exclude_unset=True),
        )
    except DomainError as error:
        _handle_domain_error(error)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(
    annotation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: AnnotationService = Depends(get_annotation_service),
):
    try:
        await service.delete(user_id, annotation_id)
    except DomainError as error:
        _handle_domain_error(error)
