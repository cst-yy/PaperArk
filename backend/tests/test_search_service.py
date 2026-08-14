"""Integration coverage for the user-scoped full-text search relation chain."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Paper, User
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_full_text_search_joins_chunk_document_and_user_scopes(
    session: AsyncSession,
) -> None:
    """PDF chunk hits must resolve through Document to the owning Paper only."""
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    session.add_all([
        User(id=owner_id, username="owner", email="owner@test.local", password_hash=""),
        User(id=other_user_id, username="other", email="other@test.local", password_hash=""),
    ])
    await session.flush()

    owner_paper = Paper(user_id=owner_id, title="Owner paper", status="ready")
    other_paper = Paper(user_id=other_user_id, title="Other paper", status="ready")
    session.add_all([owner_paper, other_paper])
    await session.flush()

    owner_document = Document(
        paper_id=owner_paper.id,
        file_path="pdfs/owner.pdf",
        parse_status="parsed",
    )
    other_document = Document(
        paper_id=other_paper.id,
        file_path="pdfs/other.pdf",
        parse_status="parsed",
    )
    session.add_all([owner_document, other_document])
    await session.flush()

    session.add_all([
        Chunk(
            document_id=owner_document.id,
            content="Federated learning improves privacy preservation.",
            page_number=7,
        ),
        Chunk(
            document_id=other_document.id,
            content="Federated learning belongs to another user.",
            page_number=3,
        ),
    ])
    await session.commit()

    results = await SearchService(session).full_text_search(
        owner_id, "federated learning"
    )

    assert len(results) == 1
    assert results[0]["paper_id"] == str(owner_paper.id)
    assert results[0]["title"] == "Owner paper"
    assert results[0]["page_number"] == 7
    assert results[0]["source"] == "chunk"
