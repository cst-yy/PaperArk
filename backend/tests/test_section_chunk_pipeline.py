"""S7-B detector, chunker, and atomic replacement tests."""

import uuid
from pathlib import Path

import fitz
import pytest
from sqlalchemy import select

from app.core.exceptions import DocumentParseError
from app.models import Document, Paper, Section, Chunk, User
from app.parsers.chunker import DerivedChunk, SectionChunker
from app.parsers.pdf_parser import PDFParser
from app.parsers.section_detector import DetectedSection, SectionDetector, TextFragment
from app.services.document_derived_service import DerivedDocumentSnapshot, DocumentDerivedService


def make_pdf(path: Path) -> None:
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "1 Introduction\nThis is the introduction paragraph.")
        page.insert_text((72, 160), "2 Method\n2.1 Training\nThis is method text.")
        page2 = pdf.new_page()
        page2.insert_text((72, 72), "3 Experiments\nResults are reported here.")
        pdf.save(path)


def test_detector_builds_hierarchy_and_ranges(tmp_path):
    path = tmp_path / "structured.pdf"
    make_pdf(path)
    parsed = PDFParser().parse(path)
    sections = SectionDetector().detect(parsed)

    assert [section.title for section in sections] == ["1 Introduction", "2 Method", "2.1 Training", "3 Experiments"]
    assert sections[2].parent_id == sections[1].id
    assert sections[0].page_start == 1
    assert sections[-1].page_end == 2


def test_detector_falls_back_to_full_text(tmp_path):
    path = tmp_path / "plain.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "A plain document without headings.")
        pdf.save(path)
    sections = SectionDetector().detect(PDFParser().parse(path))
    assert len(sections) == 1
    assert sections[0].title == "Full Text"
    assert sections[0].section_type == "other"


def test_chunker_preserves_section_boundary_and_pages(tmp_path):
    path = tmp_path / "chunks.pdf"
    make_pdf(path)
    sections = SectionDetector().detect(PDFParser().parse(path))
    chunks = SectionChunker(target_tokens=5, max_tokens=8, overlap_tokens=0).chunk(sections)
    section_ids = {section.id for section in sections}
    assert chunks
    assert all(chunk.section_id in section_ids for chunk in chunks)
    assert all(chunk.content.strip() for chunk in chunks)
    assert all(chunk.page_start <= chunk.page_end for chunk in chunks)


@pytest.mark.asyncio
async def test_atomic_replace_removes_old_rows_only_after_validation(session):
    user = User(id=uuid.uuid4(), username="derived-owner", email="derived-owner@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Derived", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/derived.pdf", page_count=1)
    session.add(document)
    await session.flush()
    old_section = Section(document_id=document.id, title="Old", level=1, order_index=0, page_start=1, page_end=1, content="old")
    session.add(old_section)
    await session.flush()

    invalid_section = DetectedSection(
        id=uuid.uuid4(), parent_id=None, title="Invalid", section_type="other",
        level=1, order_index=0, page_start=0, page_end=2,
    )
    with pytest.raises(DocumentParseError):
        await DocumentDerivedService(session).replace(
            document, DerivedDocumentSnapshot([invalid_section], [], [])
        )

    # Invalid page range is rejected before deletes.
    assert (await session.get(Section, old_section.id)) is not None


@pytest.mark.asyncio
async def test_atomic_replace_replaces_old_rows(session):
    user = User(id=uuid.uuid4(), username="replace-owner", email="replace-owner@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Replace", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/replace.pdf", page_count=1)
    session.add(document)
    await session.flush()
    old_section = Section(document_id=document.id, title="Old", level=1, order_index=0, page_start=1, page_end=1, content="old")
    session.add(old_section)
    await session.flush()

    new_section = DetectedSection(
        id=uuid.uuid4(), parent_id=None, title="New", section_type="other",
        level=1, order_index=0, page_start=1, page_end=1,
        fragments=[],
    )
    new_section.fragments.append(TextFragment(1, "new content"))
    new_chunk = DerivedChunk(
        id=uuid.uuid4(), section_id=new_section.id, order_index=0,
        content="new content", page_start=1, page_end=1, token_count=2, char_count=11,
    )
    await DocumentDerivedService(session).replace(
        document, DerivedDocumentSnapshot([new_section], [new_chunk], [])
    )
    await session.commit()

    sections = (await session.execute(select(Section).where(Section.document_id == document.id))).scalars().all()
    chunks = (await session.execute(select(Chunk).where(Chunk.document_id == document.id))).scalars().all()
    assert [section.title for section in sections] == ["New"]
    assert [chunk.content for chunk in chunks] == ["new content"]
