"""Atomic replacement of the complete PDF-derived document snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentParseError
from app.models import Chunk, Document, DocumentElement, PageBlock, Reference, Section
from app.parsers.page_block_detector import DetectedPageBlock
from app.parsers.chunker import DerivedChunk
from app.parsers.element_detector import DetectedElement
from app.parsers.reference_matcher import ReferenceMatch
from app.parsers.reference_metadata_parser import ParsedReference
from app.parsers.section_detector import DetectedSection


@dataclass(frozen=True)
class DerivedDocumentSnapshot:
    """Validated in-memory derived data, ready for one replacement transaction."""

    sections: list[DetectedSection]
    chunks: list[DerivedChunk]
    references: list[tuple[ParsedReference, ReferenceMatch]]
    elements: list[DetectedElement] = field(default_factory=list)
    page_blocks: list[DetectedPageBlock] = field(default_factory=list)


class DocumentDerivedService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def replace(self, document: Document, snapshot: DerivedDocumentSnapshot) -> None:
        self.validate(document, snapshot)
        try:
            # Explicit child-first replacement preserves the whole old snapshot on
            # any later flush failure, under the caller's savepoint.
            await self.db.execute(delete(DocumentElement).where(DocumentElement.document_id == document.id))
            # Parser-owned defaults are replaceable derived data. User-created
            # named regions are durable Reader data and must survive a reparse.
            await self.db.execute(delete(PageBlock).where(
                PageBlock.document_id == document.id,
                PageBlock.block_type != "custom",
            ))
            await self.db.execute(delete(Reference).where(Reference.document_id == document.id))
            await self.db.execute(delete(Chunk).where(Chunk.document_id == document.id))
            await self.db.execute(delete(Section).where(Section.document_id == document.id))

            for section in snapshot.sections:
                self.db.add(
                    Section(
                        id=section.id,
                        document_id=document.id,
                        parent_id=section.parent_id,
                        title=section.title,
                        section_type=section.section_type,
                        level=section.level,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        order_index=section.order_index,
                        content=section.raw_text or None,
                    )
                )
            for chunk in snapshot.chunks:
                self.db.add(
                    Chunk(
                        id=chunk.id,
                        document_id=document.id,
                        section_id=chunk.section_id,
                        page_number=chunk.page_start,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        chunk_index=chunk.order_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        char_count=chunk.char_count,
                    )
                )
            for parsed_reference, match in snapshot.references:
                self.db.add(
                    Reference(
                        document_id=document.id,
                        section_id=parsed_reference.section_id,
                        order_index=parsed_reference.order_index,
                        raw_text=parsed_reference.raw_text,
                        page_start=parsed_reference.page_start,
                        page_end=parsed_reference.page_end,
                        title=parsed_reference.title,
                        authors_json=parsed_reference.authors,
                        year=parsed_reference.year,
                        doi=parsed_reference.doi,
                        arxiv_id=parsed_reference.arxiv_id,
                        venue=parsed_reference.venue,
                        matched_paper_id=match.paper_id,
                        match_method=match.method,
                        match_confidence=match.confidence,
                    )
                )
            for element in snapshot.elements:
                self.db.add(
                    DocumentElement(
                        id=element.id, document_id=document.id, section_id=element.section_id,
                        element_type=element.element_type, order_index=element.order_index,
                        page_number=element.page_number, label=element.label,
                        caption=element.caption, raw_text=element.raw_text,
                        x=element.x, y=element.y, width=element.width, height=element.height,
                        source="pdf", confidence=element.confidence,
                    )
                )
            sections_by_page = sorted(snapshot.sections, key=lambda item: (-item.level, item.order_index))
            for block in snapshot.page_blocks:
                section_id = next((item.id for item in sections_by_page if item.page_start <= block.page_number <= item.page_end), None)
                self.db.add(PageBlock(
                    id=block.id, document_id=document.id, paper_id=document.paper_id,
                    section_id=section_id,
                    page_number=block.page_number, block_order=block.block_order,
                    reading_order=block.reading_order, block_type=block.block_type,
                    name=block.name, is_default=block.is_default,
                    column_index=block.column_index, bounding_box=block.bounding_box,
                    source_text=block.source_text, normalized_text=block.normalized_text,
                    source_hash=block.source_hash, parser_version="page-block-v1",
                ))
            await self.db.flush()
        except Exception as exc:
            raise DocumentParseError(f"derived_data_replace_error: {exc}") from exc

    @staticmethod
    def validate(document: Document, snapshot: DerivedDocumentSnapshot) -> None:
        sections = snapshot.sections
        chunks = snapshot.chunks
        references = snapshot.references
        page_blocks = snapshot.page_blocks
        section_ids = {section.id for section in sections}
        if len(section_ids) != len(sections):
            raise DocumentParseError("section order contains duplicate identities")
        if [section.order_index for section in sections] != list(range(len(sections))):
            raise DocumentParseError("section order is not contiguous")
        for section in sections:
            if not (1 <= section.page_start <= section.page_end <= document.page_count):
                raise DocumentParseError("section page range is invalid")
            if section.parent_id is not None and section.parent_id not in section_ids:
                raise DocumentParseError("section parent is outside document")
        if len({chunk.order_index for chunk in chunks}) != len(chunks):
            raise DocumentParseError("chunk order contains duplicates")
        for chunk in chunks:
            if not chunk.content.strip():
                raise DocumentParseError("empty chunk is not allowed")
            if chunk.section_id not in section_ids:
                raise DocumentParseError("chunk section is outside document")
            if not (1 <= chunk.page_start <= chunk.page_end <= document.page_count):
                raise DocumentParseError("chunk page range is invalid")

        elements = snapshot.elements
        element_orders = [element.order_index for element in elements]
        if len(set(element_orders)) != len(element_orders):
            raise DocumentParseError("element order contains duplicates")
        for element in elements:
            if element.element_type not in {"figure", "table"}:
                raise DocumentParseError("element type is invalid")
            if not element.caption.strip():
                raise DocumentParseError("element caption is empty")
            if not (1 <= element.page_number <= document.page_count):
                raise DocumentParseError("element page number is invalid")
            if element.section_id is not None and element.section_id not in section_ids:
                raise DocumentParseError("element section is outside document")
            bbox = (element.x, element.y, element.width, element.height)
            if any(value is None for value in bbox) and any(value is not None for value in bbox):
                raise DocumentParseError("element bbox must be complete or null")
            if all(value is not None for value in bbox):
                x, y, width, height = bbox
                assert x is not None and y is not None and width is not None and height is not None
                epsilon = 1e-6
                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1 and x + width <= 1 + epsilon and y + height <= 1 + epsilon):
                    raise DocumentParseError("element bbox is outside normalized page bounds")

        reference_orders = [reference.order_index for reference, _ in references]
        if len(set(reference_orders)) != len(reference_orders):
            raise DocumentParseError("reference order contains duplicates")
        reference_section_ids = {
            section.id for section in sections if section.section_type == "references"
        }
        for reference, _ in references:
            if not reference.raw_text.strip():
                raise DocumentParseError("empty reference is not allowed")
            if reference.section_id is not None and reference.section_id not in reference_section_ids:
                raise DocumentParseError("reference section must be a references section")
            if not (1 <= reference.page_start <= reference.page_end <= document.page_count):
                raise DocumentParseError("reference page range is invalid")
            if reference.doi and not reference.doi.startswith("10."):
                raise DocumentParseError("reference DOI is invalid")
            if reference.year is not None and not (1800 <= reference.year <= 2100):
                raise DocumentParseError("reference year is invalid")
        if len({(b.page_number, b.block_order) for b in page_blocks}) != len(page_blocks):
            raise DocumentParseError("page block order contains duplicates")
        if any(b.page_number < 1 or b.page_number > document.page_count for b in page_blocks):
            raise DocumentParseError("page block content or page is invalid")
        if page_blocks and (len(page_blocks) != document.page_count or any(not b.is_default for b in page_blocks)):
            raise DocumentParseError("parsed snapshot must contain exactly one default page block per page")


async def replace_document_derivatives(
    db: AsyncSession, document: Document, snapshot: DerivedDocumentSnapshot
) -> None:
    await DocumentDerivedService(db).replace(document, snapshot)
