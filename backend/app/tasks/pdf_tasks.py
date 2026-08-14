"""Async task: parse PDF into sections and chunks.

In P0 this runs synchronously. In S7+, switch to Celery.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.storage import get_full_path
from app.models import Chunk, Document, Paper, Section
from app.processors.chunker import chunker
from app.processors.pdf_parser import pdf_parser
from app.processors.structure_parser import structure_parser


async def process_pdf(paper_id: uuid.UUID) -> None:
    """Full PDF processing pipeline: parse -> structure -> chunk -> store."""
    async with async_session_factory() as db:
        # Get paper and document
        paper = await db.get(Paper, paper_id)
        if not paper or not paper.pdf_path:
            return

        stmt = select(Document).where(Document.paper_id == paper_id)
        result = await db.execute(stmt)
        document = result.scalars().first()

        if not document:
            document = Document(
                paper_id=paper_id,
                file_path=paper.pdf_path,
                parse_status="parsing",
            )
            db.add(document)
            await db.flush()
        else:
            document.parse_status = "parsing"
            await db.flush()

        # Update paper status
        paper.status = "processing"
        await db.flush()

        try:
            pdf_path = get_full_path(paper.pdf_path)

            # Step 1: Parse PDF
            parsed = pdf_parser.parse(pdf_path)
            document.page_count = parsed.page_count

            # Extract abstract if missing
            if not paper.abstract:
                abstract = pdf_parser.extract_abstract(parsed.pages)
                if abstract:
                    paper.abstract = abstract

            # Step 2: Parse structure
            sections = structure_parser.parse(parsed)

            # Store sections
            for sec in sections:
                section = Section(
                    document_id=document.id,
                    title=sec.title,
                    section_type=sec.section_type,
                    level=sec.level,
                    page_start=sec.page_start,
                    page_end=sec.page_end,
                    order_index=sec.order_index,
                    content=sec.content,
                )
                db.add(section)
            await db.flush()

            # Step 3: Chunk
            text_chunks = chunker.chunk_pages(parsed.pages)

            # Store chunks
            for tc in text_chunks:
                chunk = Chunk(
                    document_id=document.id,
                    page_number=tc.page_number,
                    chunk_index=tc.chunk_index,
                    content=tc.content,
                    token_count=tc.token_count,
                )
                db.add(chunk)
            await db.flush()

            # Update status
            document.parse_status = "parsed"
            document.parsed_at = datetime.now(timezone.utc)
            paper.status = "ready"
            await db.commit()

        except Exception as e:
            document.parse_status = "failed"
            document.parse_error = str(e)
            paper.status = "failed"
            await db.commit()
            raise
