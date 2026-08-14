"""Document service — orchestrates file access for documents.

Responsibilities:
  - User-scoped document retrieval (via Paper join)
  - Physical file resolution
  - Does NOT handle HTTP (raises domain exceptions)

The API layer calls get_document_file() which returns (Document, Path).
The API layer then constructs the FileResponse.
"""

import logging
import uuid
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentFileNotFoundError, DocumentNotFoundError
from app.core.storage import get_full_path
from app.repositories.document_repository import DocumentRepository
from app.models import Document

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    async def get_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ):
        """Get a document by ID, scoped to user_id via Paper join.

        Raises DocumentNotFoundError if the document doesn't exist
        or belongs to another user.
        """
        doc = await self.repo.get_by_id(document_id, user_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return doc

    async def get_document_file(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[Document, Path]:
        """Get a document and resolve its physical file path.

        Returns (document, full_path).
        Raises DocumentNotFoundError or DocumentFileNotFoundError.
        """
        doc = await self.get_document(user_id, document_id)

        full_path = get_full_path(doc.file_path)
        if not full_path.exists():
            logger.warning(
                "Document %s file missing on disk: %s",
                document_id,
                doc.file_path,
            )
            raise DocumentFileNotFoundError(
                f"Document file not found on disk: {doc.file_path}"
            )

        return doc, full_path


def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    """FastAPI dependency factory for DocumentService."""
    return DocumentService(db)
