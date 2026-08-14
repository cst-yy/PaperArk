"""S8-B scale fixture: 100 papers / 1k sections / 5k chunks / 2k references."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Paper, Reference, Section, User
from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_search_scale_preserves_paper_pagination_without_relation_explosion(session: AsyncSession) -> None:
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username="scale-owner", email="scale@test.local", password_hash=""))
    await session.flush()
    papers = []
    documents = []
    sections = []
    chunks = []
    references = []
    for paper_index in range(100):
        paper_id = uuid.uuid4()
        document_id = uuid.uuid4()
        title = "QuantumChromodynamics Needle" if paper_index == 42 else f"Scale paper {paper_index:03d}"
        papers.append(Paper(id=paper_id, user_id=user_id, title=title, status="ready"))
        documents.append(Document(id=document_id, paper_id=paper_id, file_path=f"pdfs/scale-{paper_index}.pdf", parse_status="ready"))
        for section_index in range(10):
            unique = " unique-scale-term" if paper_index == 42 and section_index == 0 else ""
            sections.append(Section(id=uuid.uuid4(), document_id=document_id,
                title=f"Scale section {section_index}", content=f"scaleneedle research evidence{unique}", order_index=section_index))
        for chunk_index in range(50):
            unique = " unique-scale-term" if paper_index == 42 and chunk_index == 0 else ""
            chunks.append(Chunk(id=uuid.uuid4(), document_id=document_id, chunk_index=chunk_index,
                content=f"scaleneedle chunk evidence {paper_index} {chunk_index}{unique}"))
        for reference_index in range(20):
            unique = " unique-scale-term" if paper_index == 42 and reference_index == 0 else ""
            references.append(Reference(id=uuid.uuid4(), document_id=document_id, order_index=reference_index,
                raw_text=f"scaleneedle reference {paper_index} {reference_index}{unique}", page_start=1, page_end=1))
    session.add_all(papers + documents + sections + chunks + references)
    await session.commit()

    first = await SearchService(session).search(user_id, "scaleneedle", page=1, page_size=20)
    fifth = await SearchService(session).search(user_id, "scaleneedle", page=5, page_size=20)

    assert first.total == fifth.total == 100
    assert len(first.items) == len(fifth.items) == 20
    assert all(80 <= item.match_count <= 81 for item in first.items)
    assert {item.paper.id for item in first.items}.isdisjoint(item.paper.id for item in fifth.items)
