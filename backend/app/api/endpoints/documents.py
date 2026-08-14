"""Document API endpoints — thin HTTP layer.

Endpoints:
  GET /{document_id}           — document metadata
  GET /{document_id}/file      — serve the PDF file (inline, for browser/PDF.js)
  GET /{document_id}/sections  — section tree (for future use)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    DocumentFileNotFoundError,
    DocumentNotFoundError,
    StorageError,
)
from app.models import Section
from app.schemas.document import DocumentResponse, SectionResponse
from app.services.document_service import DocumentService, get_document_service

router = APIRouter()

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
):
    """Get the section tree (table of contents) for a document."""
    stmt = (
        select(Section)
        .where(Section.document_id == document_id)
        .order_by(Section.order_index)
    )
    result = await db.execute(stmt)
    sections = result.scalars().all()

    # Build tree
    section_map: dict[uuid.UUID, SectionResponse] = {}
    roots: list[SectionResponse] = []

    for s in sections:
        resp = SectionResponse(
            id=s.id,
            document_id=s.document_id,
            parent_id=s.parent_id,
            title=s.title,
            section_type=s.section_type,
            level=s.level,
            page_start=s.page_start,
            page_end=s.page_end,
            order_index=s.order_index,
            children=[],
        )
        section_map[s.id] = resp

    for s in sections:
        resp = section_map[s.id]
        if s.parent_id and s.parent_id in section_map:
            section_map[s.parent_id].children.append(resp)
        else:
            roots.append(resp)

    return roots
