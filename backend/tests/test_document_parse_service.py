"""S7-A parser lifecycle tests."""

import uuid
from pathlib import Path

import fitz
import pytest

from app.core.exceptions import DocumentNotFoundError, DocumentParseInProgressError
from app.models import Document, Paper, User
from app.parsers.pdf_parser import PDFParser
from app.services.document_parse_service import DocumentParseService


async def create_document(session, user_id: uuid.UUID, file_path: str = "pdfs/test.pdf"):
    paper = Paper(user_id=user_id, title="Parser test", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=file_path, parse_status="pending")
    session.add(document)
    await session.flush()
    return paper, document


def write_pdf(path: Path, text: str = "Hello parser") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), text)
        pdf.save(path)


def test_pdf_parser_extracts_multiple_pages_and_warns_for_empty_page(tmp_path):
    source = tmp_path / "multi-page.pdf"
    with fitz.open() as pdf:
        first = pdf.new_page()
        first.insert_text((72, 72), "English text")
        pdf.new_page()
        pdf.save(source)

    parsed = PDFParser().parse(source)

    assert parsed.page_count == 2
    assert parsed.pages[0].text == "English text"
    assert parsed.pages[0].width > 0 and parsed.pages[0].height > 0
    assert parsed.pages[1].text == ""
    assert len(parsed.warnings) == 1


@pytest.mark.asyncio
async def test_parse_success_records_state_and_version(session, tmp_path, monkeypatch):
    user = User(id=uuid.uuid4(), username="parser-owner", email="parser-owner@test.local", password_hash="")
    session.add(user)
    await session.flush()
    _, document = await create_document(session, user.id, "pdfs/test.pdf")
    source = tmp_path / "test.pdf"
    write_pdf(source, "A page of extracted text")
    monkeypatch.setattr("app.services.document_parse_service.get_full_path", lambda _: source)

    result = await DocumentParseService(session).parse_document(user.id, document.id)

    assert result.parse_status == "ready"
    assert result.page_count == 1
    assert result.parser_version == "pdf-parser-v1"
    assert result.parsed_at is not None
    assert result.parse_error is None
    assert source.exists()


@pytest.mark.asyncio
async def test_parse_failure_preserves_source_and_can_retry(session, tmp_path, monkeypatch):
    user = User(id=uuid.uuid4(), username="parser-retry", email="parser-retry@test.local", password_hash="")
    session.add(user)
    await session.flush()
    _, document = await create_document(session, user.id, "pdfs/retry.pdf")
    source = tmp_path / "retry.pdf"
    source.write_bytes(b"not a valid pdf")
    monkeypatch.setattr("app.services.document_parse_service.get_full_path", lambda _: source)
    service = DocumentParseService(session)

    with pytest.raises(Exception):
        await service.parse_document(user.id, document.id)
    assert source.read_bytes() == b"not a valid pdf"
    failed = await service.get_parse_status(user.id, document.id)
    assert failed.parse_status == "failed"
    assert failed.parse_error

    write_pdf(source, "Retry succeeds")
    retried = await service.parse_document(user.id, document.id)
    assert retried.parse_status == "ready"
    assert retried.parser_version == "pdf-parser-v1"


@pytest.mark.asyncio
async def test_foreign_document_is_rejected(session):
    owner = User(id=uuid.uuid4(), username="parser-user-a", email="parser-a@test.local", password_hash="")
    other = User(id=uuid.uuid4(), username="parser-user-b", email="parser-b@test.local", password_hash="")
    session.add_all([owner, other])
    await session.flush()
    _, document = await create_document(session, owner.id)

    with pytest.raises(DocumentNotFoundError):
        await DocumentParseService(session).parse_document(other.id, document.id)


@pytest.mark.asyncio
async def test_processing_document_rejects_duplicate(session):
    user = User(id=uuid.uuid4(), username="parser-lock", email="parser-lock@test.local", password_hash="")
    session.add(user)
    await session.flush()
    _, document = await create_document(session, user.id)
    document.parse_status = "processing"
    await session.flush()

    with pytest.raises(DocumentParseInProgressError):
        await DocumentParseService(session).parse_document(user.id, document.id)
