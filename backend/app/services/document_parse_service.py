"""Document parse lifecycle orchestration for S7-C.

The PDF source is parsed once. Sections, chunks, and references are derived in
memory, validated as one snapshot, then atomically replaced without touching
Paper metadata or source files.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    DocumentFileNotFoundError,
    DocumentNotFoundError,
    DocumentParseInProgressError,
)
from app.core.storage import get_full_path
from app.models import Document
from app.parsers.chunker import SectionChunker
from app.parsers.element_detector import ElementDetector
from app.parsers.pdf_parser import PDFParser
from app.parsers.reference_matcher import ReferenceMatcher
from app.parsers.reference_metadata_parser import ReferenceMetadataParser
from app.parsers.reference_segmenter import ReferenceSegmenter
from app.parsers.section_detector import SectionDetector
from app.repositories.document_repository import DocumentRepository
from app.services.document_derived_service import DerivedDocumentSnapshot, DocumentDerivedService

logger = logging.getLogger(__name__)


class DocumentParseService:
    def __init__(
        self,
        db: AsyncSession,
        parser: PDFParser | None = None,
        section_detector: SectionDetector | None = None,
        chunker: SectionChunker | None = None,
        reference_segmenter: ReferenceSegmenter | None = None,
        reference_metadata_parser: ReferenceMetadataParser | None = None,
        element_detector: ElementDetector | None = None,
    ):
        self.db = db
        self.repo = DocumentRepository(db)
        self.parser = parser or PDFParser()
        self.section_detector = section_detector or SectionDetector()
        self.chunker = chunker or SectionChunker()
        self.reference_segmenter = reference_segmenter or ReferenceSegmenter()
        self.reference_metadata_parser = reference_metadata_parser or ReferenceMetadataParser()
        self.element_detector = element_detector or ElementDetector()

    async def get_parse_status(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self.repo.get_by_id(document_id, user_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return document

    async def parse_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        """Parse and atomically replace this Document's complete derived snapshot."""
        document = await self.repo.get_by_id(document_id, user_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.parse_status == "processing":
            raise DocumentParseInProgressError("文档正在解析中，请稍后再试")

        claimed = await self.db.execute(
            update(Document)
            .where(Document.id == document_id, Document.parse_status != "processing")
            .values(parse_status="processing", parse_error=None)
        )
        if claimed.rowcount != 1:
            raise DocumentParseInProgressError("文档正在解析中，请稍后再试")
        await self.db.commit()

        try:
            full_path = self._resolve_source(document)
            parsed = await asyncio.to_thread(self.parser.parse, full_path)
            document.page_count = parsed.page_count
            sections = self.section_detector.detect(parsed)
            chunks = self.chunker.chunk(sections)
            candidates = self.reference_segmenter.segment(sections)
            metadata = [self.reference_metadata_parser.parse(candidate) for candidate in candidates]
            matcher = ReferenceMatcher(self.db)
            references = [(reference, await matcher.match(user_id, reference)) for reference in metadata]
            elements = self.element_detector.detect(parsed, sections)
            snapshot = DerivedDocumentSnapshot(sections=sections, chunks=chunks, references=references, elements=elements)
            DocumentDerivedService.validate(document, snapshot)
        except Exception as exc:
            logger.exception("Document %s parsing/derivation failed", document_id)
            await self._mark_failed(document_id, str(exc))
            raise

        try:
            # This savepoint protects every old derived row on replacement failure.
            async with self.db.begin_nested():
                await DocumentDerivedService(self.db).replace(document, snapshot)
                await self.db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        page_count=parsed.page_count,
                        parse_status="ready",
                        parse_error=None,
                        parsed_at=datetime.now(timezone.utc),
                        parser_version=self.parser.version,
                    )
                )
            await self.db.commit()
        except Exception as exc:
            logger.exception("Document %s derived replacement failed", document_id)
            await self.db.rollback()
            await self._mark_failed(document_id, str(exc))
            raise

        refreshed = await self.repo.get_by_id(document_id, user_id)
        if not refreshed:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return refreshed

    @staticmethod
    def _resolve_source(document: Document) -> Path:
        full_path = get_full_path(document.file_path)
        if not full_path.is_file():
            raise DocumentFileNotFoundError("文档源 PDF 文件不存在")
        return full_path

    async def _mark_failed(self, document_id: uuid.UUID, error: str) -> None:
        await self.db.rollback()
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(parse_status="failed", parse_error=error[:4000])
        )
        await self.db.commit()


def get_document_parse_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentParseService:
    return DocumentParseService(db)
