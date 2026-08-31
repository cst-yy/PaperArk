"""User-managed named PDF page regions."""
from __future__ import annotations

import asyncio
import hashlib
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_full_path
from app.models import PageBlock, TranslationBlock
from app.parsers.pdf_parser import PDFParser
from app.repositories.document_repository import DocumentRepository
from app.schemas.translation import CustomPageBlockCreate, CustomPageBlockUpdate, PageBlockBBox


class PageBlockService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.documents = DocumentRepository(db)

    async def list(self, user_id: uuid.UUID, document_id: uuid.UUID, page_number: int | None = None, query: str | None = None) -> list[PageBlock]:
        document = await self.documents.get_by_id(document_id, user_id)
        if not document:
            raise LookupError("Document not found")
        statement = select(PageBlock).where(PageBlock.document_id == document_id)
        if page_number is not None:
            statement = statement.where(PageBlock.page_number == page_number)
        if query and query.strip():
            statement = statement.where(PageBlock.name.ilike(f"%{query.strip()}%"))
        return list((await self.db.scalars(statement.order_by(PageBlock.page_number, PageBlock.is_default.desc(), PageBlock.block_order))).all())

    async def create(self, user_id: uuid.UUID, document_id: uuid.UUID, data: CustomPageBlockCreate) -> PageBlock:
        document = await self.documents.get_by_id(document_id, user_id)
        if not document:
            raise LookupError("Document not found")
        if data.page_number > (document.page_count or 0):
            raise ValueError("page_number is outside the document")
        bbox = data.bounding_box.as_dict()
        source_text = await self._extract(document.file_path, data.page_number, data.bounding_box)
        normalized = " ".join(source_text.split())
        block_order = (await self.db.scalar(select(func.max(PageBlock.block_order)).where(
            PageBlock.document_id == document_id, PageBlock.page_number == data.page_number)))
        reading_order = (await self.db.scalar(select(func.max(PageBlock.reading_order)).where(PageBlock.document_id == document_id)))
        row = PageBlock(
            document_id=document.id, paper_id=document.paper_id, page_number=data.page_number,
            block_order=(block_order if block_order is not None else -1) + 1,
            reading_order=(reading_order if reading_order is not None else -1) + 1,
            block_type="custom", name=data.name.strip(), is_default=False, column_index=None,
            bounding_box=bbox, source_text=source_text, normalized_text=normalized,
            source_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(), parser_version="custom-page-block-v1",
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(self, user_id: uuid.UUID, block_id: uuid.UUID, data: CustomPageBlockUpdate) -> PageBlock:
        row, document = await self._owned(user_id, block_id)
        if data.name is not None:
            row.name = data.name.strip()
        if data.text_style is not None:
            row.text_style = data.text_style.model_dump()
        if data.bounding_box is not None:
            row.bounding_box = data.bounding_box.as_dict()
            row.source_text = await self._extract(document.file_path, row.page_number, data.bounding_box)
            row.normalized_text = " ".join(row.source_text.split())
            row.source_hash = hashlib.sha256(row.normalized_text.encode("utf-8")).hexdigest()
            translations = list((await self.db.scalars(select(TranslationBlock).where(TranslationBlock.page_block_id == row.id))).all())
            for translation in translations:
                if translation.user_translation:
                    translation.source_hash = row.source_hash
                    translation.machine_translation = None
                    translation.status = "manual"
                    translation.revision += 1
                else:
                    await self.db.delete(translation)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, user_id: uuid.UUID, block_id: uuid.UUID) -> None:
        row, _ = await self._owned(user_id, block_id)
        await self.db.execute(delete(TranslationBlock).where(TranslationBlock.page_block_id == row.id))
        await self.db.delete(row)
        await self.db.commit()

    async def _owned(self, user_id: uuid.UUID, block_id: uuid.UUID):
        row = await self.db.get(PageBlock, block_id)
        if not row:
            raise LookupError("Page block not found")
        document = await self.documents.get_by_id(row.document_id, user_id)
        if not document:
            raise LookupError("Page block not found")
        return row, document

    @staticmethod
    async def _extract(file_path: str, page_number: int, bbox: PageBlockBBox) -> str:
        parsed = await asyncio.to_thread(PDFParser().parse, get_full_path(file_path))
        page = parsed.pages[page_number - 1]
        selected = []
        for block in page.blocks:
            center_x = ((block.x0 + block.x1) / 2) / page.width
            center_y = ((block.y0 + block.y1) / 2) / page.height
            if bbox.x <= center_x <= bbox.x + bbox.width and bbox.y <= center_y <= bbox.y + bbox.height:
                selected.append(block)
        selected.sort(key=lambda item: (item.y0, item.x0))
        return " ".join(item.text.strip() for item in selected if item.text.strip())
