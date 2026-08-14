"""Integration tests for paper deletion and PDF cleanup."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper, User
from app.services.paper_service import PaperService


@pytest.mark.asyncio
async def test_delete_paper_cleans_every_document_and_legacy_file(
    session: AsyncSession, tmp_path, monkeypatch
) -> None:
    user_id = uuid.uuid4()
    session.add(
        User(id=user_id, username="owner", email="owner@test.local", password_hash="")
    )
    await session.flush()

    paths = ["pdfs/first.pdf", "pdfs/second.pdf", "pdfs/legacy.pdf"]
    files = {path: tmp_path / path.replace("/", "-") for path in paths}
    for file_path in files.values():
        file_path.write_bytes(b"%PDF-test")

    paper = Paper(
        user_id=user_id,
        title="Multiple documents",
        status="imported",
        pdf_path=paths[2],
    )
    session.add(paper)
    await session.flush()
    session.add_all([
        Document(paper_id=paper.id, file_path=paths[0], parse_status="pending"),
        Document(paper_id=paper.id, file_path=paths[1], parse_status="pending"),
    ])
    await session.commit()

    monkeypatch.setattr(
        "app.services.paper_service.get_full_path", lambda path: files[path]
    )
    await PaperService(session).delete_paper(user_id, paper.id)

    assert await session.get(Paper, paper.id) is None
    documents = await session.scalars(
        select(Document).where(Document.paper_id == paper.id)
    )
    assert documents.all() == []
    assert all(not file_path.exists() for file_path in files.values())
