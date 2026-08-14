"""Integration tests for document user isolation."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper, User
from app.repositories.document_repository import DocumentRepository


@pytest.mark.asyncio
async def test_document_lookup_is_scoped_through_owning_paper(
    session: AsyncSession,
) -> None:
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    session.add_all([
        User(id=owner_id, username="owner", email="owner@test.local", password_hash=""),
        User(id=other_user_id, username="other", email="other@test.local", password_hash=""),
    ])
    await session.flush()

    paper = Paper(user_id=owner_id, title="Private paper", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(
        paper_id=paper.id,
        file_path="pdfs/private.pdf",
        parse_status="pending",
    )
    session.add(document)
    await session.commit()

    repository = DocumentRepository(session)
    assert await repository.get_by_id(document.id, owner_id) is not None
    assert await repository.get_by_id(document.id, other_user_id) is None
    assert await repository.get_by_paper(paper.id, other_user_id) is None
    assert await repository.list_by_paper(paper.id, owner_id) == [document]
    assert await repository.list_by_paper(paper.id, other_user_id) == []
