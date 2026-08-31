"""Document API endpoints — thin HTTP layer.

Endpoints:
  GET /{document_id}           — document metadata
  GET /{document_id}/file      — serve the PDF file (inline, for browser/PDF.js)
  GET /{document_id}/sections  — section tree (for future use)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    DocumentFileNotFoundError,
    DocumentNotFoundError,
    DocumentParseInProgressError,
    StorageError,
)
from app.models import Section
from app.schemas.document import DocumentElementResponse, DocumentResponse, ElementBBox, MatchedPaperBrief, ReferenceResponse, SectionResponse
from app.repositories.document_repository import DocumentRepository
from app.services.document_parse_service import (
    DocumentParseService,
    get_document_parse_service,
)
from app.services.document_service import DocumentService, get_document_service
from app.services.document_element_service import DocumentElementService, get_document_element_service
from app.services.reference_service import ReferenceService, get_reference_service
from app.services.page_block_service import PageBlockService
from app.schemas.translation import CustomPageBlockCreate, CustomPageBlockUpdate, PageBlockResponse

router = APIRouter()


@router.get("/{document_id}/page-blocks", response_model=list[PageBlockResponse])
async def list_page_blocks(document_id: uuid.UUID, page_number: int | None = Query(None, ge=1), q: str | None = Query(None, max_length=255), db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await PageBlockService(db).list(user_id, document_id, page_number, q)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc


@router.post("/{document_id}/page-blocks", response_model=PageBlockResponse, status_code=201)
async def create_page_block(document_id: uuid.UUID, data: CustomPageBlockCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await PageBlockService(db).create(user_id, document_id, data)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc


@router.patch("/page-blocks/{block_id}", response_model=PageBlockResponse)
async def update_page_block(block_id: uuid.UUID, data: CustomPageBlockUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await PageBlockService(db).update(user_id, block_id, data)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc


@router.delete("/page-blocks/{block_id}", status_code=204)
async def delete_page_block(block_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: await PageBlockService(db).delete(user_id, block_id)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc
    return Response(status_code=204)

# ── Exception -> HTTP status code mapping ──

_DOC_EXCEPTION_STATUS = {
    DocumentNotFoundError: 404,
    DocumentFileNotFoundError: 404,
    StorageError: 500,
}


def _handle_doc_error(e: Exception) -> HTTPException:
    status_code = _DOC_EXCEPTION_STATUS.get(type(e), 400)
    detail = e.message if hasattr(e, "message") else str(e)
    return HTTPException(status_code=status_code, detail=detail)


# ────────────────────────────── Detail ──────────────────────────────

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get document metadata by ID (user-scoped)."""
    try:
        doc = await service.get_document(user_id, document_id)
    except DocumentNotFoundError as e:
        raise _handle_doc_error(e)
    return doc


# ────────────────────────────── File ────────────────────────────────

@router.get("/{document_id}/parse-status", response_model=DocumentResponse)
async def get_document_parse_status(
    document_id: uuid.UUID,
    service: DocumentParseService = Depends(get_document_parse_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.get_parse_status(user_id, document_id)
    except DocumentNotFoundError as e:
        raise _handle_doc_error(e)


@router.post("/{document_id}/parse", response_model=DocumentResponse)
async def parse_document(
    document_id: uuid.UUID,
    service: DocumentParseService = Depends(get_document_parse_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await service.parse_document(user_id, document_id)
    except DocumentParseInProgressError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except (DocumentNotFoundError, DocumentFileNotFoundError) as e:
        raise _handle_doc_error(e)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 解析失败: {e}")


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Serve the PDF file for inline viewing in the browser.

    Returns:
      - 200 + FileResponse with Content-Type: application/pdf
      - Content-Disposition: inline (so the browser displays, not downloads)
      - filename set to original_filename for "Save As" scenarios

    PDF.js in S4 will consume this endpoint directly.
    """
    try:
        doc, full_path = await service.get_document_file(user_id, document_id)
    except (DocumentNotFoundError, DocumentFileNotFoundError, StorageError) as e:
        raise _handle_doc_error(e)

    return FileResponse(
        path=str(full_path),
        media_type="application/pdf",
        # Omit filename to preserve browser inline rendering and avoid manually
        # interpolating untrusted original filenames into response headers.
        headers={"Content-Disposition": "inline"},
    )


# ────────────────────────────── Sections ────────────────────────────

@router.get("/{document_id}/sections", response_model=list[SectionResponse])
async def get_sections(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get the parsed section tree for a user-owned document."""
    document = await DocumentRepository(db).get_by_id(document_id, user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    stmt = (
        select(Section)
        .where(Section.document_id == document_id)
        .order_by(Section.order_index)
    )
    result = await db.execute(stmt)
    sections = result.scalars().all()

    return [
        SectionResponse(
            id=section.id,
            document_id=section.document_id,
            parent_id=section.parent_id,
            title=section.title,
            section_type=section.section_type,
            level=section.level,
            page_start=section.page_start,
            page_end=section.page_end,
            order_index=section.order_index,
            raw_text=section.content,
            children=[],
        )
        for section in sections
    ]


@router.get("/{document_id}/elements", response_model=list[DocumentElementResponse])
async def get_document_elements(
    document_id: uuid.UUID,
    element_type: str | None = None,
    service: DocumentElementService = Depends(get_document_element_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get PDF-derived figure/table metadata for a user-owned document."""
    if element_type is not None and element_type not in {"figure", "table"}:
        raise HTTPException(status_code=422, detail="element_type must be figure or table")
    elements = await service.list_for_document(user_id, document_id, element_type)
    if elements is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return [
        DocumentElementResponse(
            id=element.id, document_id=element.document_id, section_id=element.section_id,
            element_type=element.element_type, order_index=element.order_index,
            page_number=element.page_number, label=element.label, caption=element.caption,
            raw_text=element.raw_text,
            bbox=(ElementBBox(x=element.x, y=element.y, width=element.width, height=element.height)
                  if element.x is not None else None),
            source=element.source, confidence=element.confidence,
        )
        for element in elements
    ]


@router.get("/{document_id}/references", response_model=list[ReferenceResponse])
async def get_references(
    document_id: uuid.UUID,
    service: ReferenceService = Depends(get_reference_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get PDF-derived references for a user-owned document."""
    references = await service.list_for_document(user_id, document_id)
    if references is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return [
        ReferenceResponse(
            id=reference.id,
            document_id=reference.document_id,
            section_id=reference.section_id,
            order_index=reference.order_index,
            raw_text=reference.raw_text,
            title=reference.title,
            authors=reference.authors_json,
            year=reference.year,
            doi=reference.doi,
            arxiv_id=reference.arxiv_id,
            venue=reference.venue,
            page_start=reference.page_start,
            page_end=reference.page_end,
            matched_paper=(
                MatchedPaperBrief(id=reference.matched_paper.id, title=reference.matched_paper.title)
                if reference.matched_paper else None
            ),
            match_method=reference.match_method,
            match_confidence=reference.match_confidence,
        )
        for reference in references
    ]
