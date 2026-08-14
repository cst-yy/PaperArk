"""Paper API endpoints — thin HTTP layer.

Responsibilities:
  - Parse HTTP request (params, body, file)
  - Call PaperService
  - Convert service result to Pydantic response
  - Catch domain exceptions and convert to HTTP errors

Does NOT: write SQL, contain business logic, validate PDF content,
or manage transactions. All of that lives in Service + Storage.
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    DocumentNotFoundError,
    DuplicatePaperError,
    FileTooLargeError,
    FolderNotFoundError,
    InvalidFileTypeError,
    InvalidFolderError,
    InvalidNoteError,
    InvalidTagError,
    PaperNotFoundError,
    StorageError,
    TagNotFoundError,
)
from app.schemas.keyword import KeywordReplacement
from app.schemas.reading_progress import ReadingProgressResponse, ReadingProgressUpsert
from app.schemas.note import NoteResponse
from app.schemas.paper import (
    AuthorReplacement,
    FolderReplacement,
    PaperCreate,
    PaperMetadataReplaceRequest,
    ReadingStatus,
    ReadingStatusUpdate,
    TagReplacement,
    PaperPageResponse,
    PaperResponse,
    PaperUpdate,
)
from app.services.paper_service import PaperMapper, PaperService, get_paper_service
from app.services.reading_progress_service import ReadingProgressService
from app.services.note_service import NoteService

router = APIRouter()

# ── Exception -> HTTP status code mapping ──

_EXCEPTION_STATUS = {
    PaperNotFoundError: 404,
    TagNotFoundError: 404,
    FolderNotFoundError: 404,
    DocumentNotFoundError: 404,
    DuplicatePaperError: 409,
    InvalidTagError: 400,
    InvalidFolderError: 400,
    InvalidFileTypeError: 400,
    FileTooLargeError: 413,
    StorageError: 500,
}


def _handle_domain_error(e: Exception) -> HTTPException:
    """Convert a domain exception to an HTTPException."""
    status_code = _EXCEPTION_STATUS.get(type(e), 400)
    detail = e.message if hasattr(e, "message") else str(e)
    return HTTPException(status_code=status_code, detail=detail)


# ────────────────────────────── Upload ──────────────────────────────

@router.post("/upload", response_model=PaperResponse)
async def upload_paper(
    file: UploadFile = File(...),
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Upload a PDF and create a paper + document record.

    PDF validation (extension, content-type, magic bytes, size) is
    handled by the service layer via storage.validate_pdf().
    """
    try:
        paper = await service.import_pdf(user_id, file)
    except (InvalidFileTypeError, FileTooLargeError, StorageError) as e:
        raise _handle_domain_error(e)
    return PaperMapper.to_detail_response(paper)


# ────────────────────────────── Create ──────────────────────────────

@router.post("/", response_model=PaperResponse)
async def create_paper(
    data: PaperCreate,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a paper from metadata."""
    try:
        paper = await service.create_paper(user_id, data)
    except (DuplicatePaperError, InvalidTagError, InvalidFolderError) as e:
        raise _handle_domain_error(e)
    return PaperMapper.to_detail_response(paper)


# ────────────────────────────── List ────────────────────────────────

@router.get("/", response_model=PaperPageResponse)
async def list_papers(
    q: str | None = Query(None, description="搜索标题/摘要"),
    folder_id: uuid.UUID | None = Query(None),
    tag_id: uuid.UUID | None = Query(None),
    year: int | None = Query(None),
    starred: bool | None = Query(None),
    status: str | None = Query(None, description="处理状态"),
    reading_status: ReadingStatus | None = Query(None, description="阅读状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List papers with optional filters and pagination."""
    return await service.list_papers(
        user_id=user_id,
        q=q,
        folder_id=folder_id,
        tag_id=tag_id,
        year=year,
        starred=starred,
        status=status,
        reading_status=reading_status,
        page=page,
        page_size=page_size,
    )


# ────────────────────────────── Detail ──────────────────────────────

@router.get("/{paper_id}/notes", response_model=list[NoteResponse])
async def list_paper_notes(
    paper_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await NoteService(db).list_notes(user_id, paper_id)
    except InvalidNoteError as error:
        raise HTTPException(status_code=404, detail=error.message)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get a single paper by ID."""
    try:
        paper = await service.get_paper(user_id, paper_id)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return PaperMapper.to_detail_response(paper)


# ──────────────────────── Reading progress ─────────────────────────

@router.get("/{paper_id}/reading-progress", response_model=ReadingProgressResponse | None)
async def get_reading_progress(
    paper_id: uuid.UUID,
    document_id: uuid.UUID = Query(..., description="当前阅读的 PDF Document ID"),
    db = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Return the current user's saved position for this concrete PDF."""
    try:
        return await ReadingProgressService(db).get_progress(user_id, paper_id, document_id)
    except (PaperNotFoundError, DocumentNotFoundError) as error:
        raise _handle_domain_error(error)


@router.put("/{paper_id}/reading-progress", response_model=ReadingProgressResponse)
async def upsert_reading_progress(
    paper_id: uuid.UUID,
    data: ReadingProgressUpsert,
    db = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create or update the current user's position for a concrete PDF."""
    try:
        return await ReadingProgressService(db).upsert_progress(user_id, paper_id, data)
    except (PaperNotFoundError, DocumentNotFoundError) as error:
        raise _handle_domain_error(error)


# ────────────────────────────── Update ──────────────────────────────

@router.patch("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: uuid.UUID,
    data: PaperUpdate,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update paper metadata."""
    try:
        paper = await service.update_paper(user_id, paper_id, data)
    except (PaperNotFoundError, DuplicatePaperError) as e:
        raise _handle_domain_error(e)
    return PaperMapper.to_detail_response(paper)


# ──────────────────────── Reading status ───────────────────────────

@router.put("/{paper_id}/reading-status", response_model=PaperResponse)
async def set_reading_status(
    paper_id: uuid.UUID,
    data: ReadingStatusUpdate,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Set the user-defined Paper-level reading workflow status."""
    try:
        paper = await service.set_reading_status(user_id, paper_id, data.reading_status)
    except PaperNotFoundError as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(await service.get_paper(user_id, paper.id))


# ────────────────────────────── Delete ──────────────────────────────

@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a paper and its associated file."""
    try:
        await service.delete_paper(user_id, paper_id)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return {"message": "论文已删除"}


# ────────────────────────────── Star ────────────────────────────────

@router.put("/{paper_id}/star")
async def star_paper(
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Star a paper (idempotent)."""
    try:
        await service.set_starred(user_id, paper_id, True)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return {"is_starred": True}


@router.delete("/{paper_id}/star")
async def unstar_paper(
    paper_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Unstar a paper (idempotent)."""
    try:
        await service.set_starred(user_id, paper_id, False)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return {"is_starred": False}


# ────────────────── Aggregate replacement endpoints ────────────────

@router.put("/{paper_id}/metadata", response_model=PaperResponse)
async def replace_metadata_aggregate(
    paper_id: uuid.UUID,
    data: PaperMetadataReplaceRequest,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Atomically save every editor-owned Paper metadata field and collection."""
    try:
        paper = await service.replace_metadata_aggregate(user_id, paper_id, data)
    except (PaperNotFoundError, DuplicatePaperError, InvalidTagError, InvalidFolderError) as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(paper)


@router.put("/{paper_id}/authors", response_model=PaperResponse)
async def replace_authors(
    paper_id: uuid.UUID,
    data: AuthorReplacement,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        paper = await service.replace_authors(user_id, paper_id, data.authors)
    except PaperNotFoundError as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(paper)


@router.put("/{paper_id}/tags", response_model=PaperResponse)
async def replace_tags(
    paper_id: uuid.UUID,
    data: TagReplacement,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        paper = await service.replace_tags(user_id, paper_id, data.tag_ids)
    except (PaperNotFoundError, InvalidTagError) as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(paper)


@router.put("/{paper_id}/keywords", response_model=PaperResponse)
async def replace_keywords(
    paper_id: uuid.UUID,
    data: KeywordReplacement,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        paper = await service.replace_keywords(user_id, paper_id, data)
    except PaperNotFoundError as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(paper)


@router.put("/{paper_id}/folders", response_model=PaperResponse)
async def replace_folders(
    paper_id: uuid.UUID,
    data: FolderReplacement,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        paper = await service.replace_folders(user_id, paper_id, data.folder_ids)
    except (PaperNotFoundError, InvalidFolderError) as error:
        raise _handle_domain_error(error)
    return PaperMapper.to_detail_response(paper)


# ──────────────────── Paper-centric Tag endpoints ───────────────────

@router.post("/{paper_id}/tags/{tag_id}")
async def add_tag_to_paper(
    paper_id: uuid.UUID,
    tag_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Add a tag to a paper."""
    try:
        await service.add_tag(user_id, paper_id, tag_id)
    except (PaperNotFoundError, TagNotFoundError) as e:
        raise _handle_domain_error(e)
    return {"message": "标签已添加"}


@router.delete("/{paper_id}/tags/{tag_id}")
async def remove_tag_from_paper(
    paper_id: uuid.UUID,
    tag_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Remove a tag from a paper."""
    try:
        await service.remove_tag(user_id, paper_id, tag_id)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return {"message": "标签已移除"}


# ────────────────── Paper-centric Folder endpoints ──────────────────

@router.post("/{paper_id}/folders/{folder_id}")
async def add_paper_to_folder(
    paper_id: uuid.UUID,
    folder_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Add a paper to a folder."""
    try:
        await service.add_folder(user_id, paper_id, folder_id)
    except (PaperNotFoundError, FolderNotFoundError) as e:
        raise _handle_domain_error(e)
    return {"message": "已添加到文件夹"}


@router.delete("/{paper_id}/folders/{folder_id}")
async def remove_paper_from_folder(
    paper_id: uuid.UUID,
    folder_id: uuid.UUID,
    service: PaperService = Depends(get_paper_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Remove a paper from a folder."""
    try:
        await service.remove_folder(user_id, paper_id, folder_id)
    except PaperNotFoundError as e:
        raise _handle_domain_error(e)
    return {"message": "已从文件夹移除"}
