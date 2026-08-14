import math
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SemanticRetrievalError
from app.models import Chunk, Document, Note, Paper, User
from app.services.search_service import SearchService


def vector(axis: int, secondary: float = 0.0) -> list[float]:
    values = [0.0] * 384
    values[axis] = 1.0
    if secondary:
        values[(axis + 1) % 384] = secondary
        norm = math.sqrt(1 + secondary * secondary)
        values = [value / norm for value in values]
    return values


class SemanticFakeProvider:
    model_name = "semantic-fake-v1"
    dimension = 384

    def __init__(self, query_vector: list[float] | None = None, fail: bool = False):
        self.query_vector = query_vector or vector(0)
        self.fail = fail

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            raise RuntimeError("query embedding unavailable")
        return [self.query_vector for _ in texts]


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(user)
    await session.flush()
    return user


async def add_paper_chunk(session: AsyncSession, user: User, title: str, content: str,
                          embedding: list[float], *, status: str = "ready", model: str = "semantic-fake-v1"):
    paper = Paper(user_id=user.id, title=title, status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=f"pdfs/{paper.id}.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    chunk = Chunk(document_id=document.id, chunk_index=0, content=content, page_start=2,
        embedding=embedding, embedding_status=status, embedding_model=model,
        embedding_dimension=384, embedding_content_hash="x")
    session.add(chunk)
    await session.flush()
    return paper, chunk


@pytest.mark.asyncio
async def test_semantic_retrieval_ranks_synonym_chunks_and_note(session: AsyncSession) -> None:
    owner = await make_user(session, "semantic-owner")
    relevant, relevant_chunk = await add_paper_chunk(session, owner, "Federated systems",
        "label distribution heterogeneity between participating clients", vector(0))
    await add_paper_chunk(session, owner, "Vision systems", "image segmentation pixels", vector(1))
    # A second relevant chunk must aggregate into the same Paper entity.
    session.add(Chunk(document_id=relevant_chunk.document_id, chunk_index=1, content="non IID client populations",
        embedding=vector(0, 0.1), embedding_status="ready", embedding_model="semantic-fake-v1",
        embedding_dimension=384, embedding_content_hash="y"))
    note = Note(user_id=owner.id, note_type="general", title="Distributed training thought",
        content_markdown="clients have different class proportions", embedding=vector(0, 0.2),
        embedding_status="ready", embedding_model="semantic-fake-v1", embedding_dimension=384,
        embedding_content_hash="z")
    session.add(note)
    await session.commit()

    response = await SearchService(session, SemanticFakeProvider()).search(
        owner.id, "class imbalance across clients", mode="semantic")
    assert response.total == 2
    paper_result = next(item for item in response.items if item.entity_type == "paper" and item.paper.id == relevant.id)
    assert paper_result.match_count == 2
    assert paper_result.matches[0].source == "chunk" and paper_result.matches[0].page_start == 2
    assert any(item.entity_type == "note" and item.note.id == note.id for item in response.items)


@pytest.mark.asyncio
async def test_semantic_filters_lifecycle_model_and_user(session: AsyncSession) -> None:
    owner = await make_user(session, "semantic-filter-owner")
    foreign = await make_user(session, "semantic-filter-foreign")
    visible, _ = await add_paper_chunk(session, owner, "Visible", "ready current", vector(0))
    for status in ("pending", "processing", "failed"):
        await add_paper_chunk(session, owner, status, "stale vector", vector(0), status=status)
    await add_paper_chunk(session, owner, "old model", "old model vector", vector(0), model="model-a")
    await add_paper_chunk(session, foreign, "Foreign", "foreign vector", vector(0))
    await session.commit()
    response = await SearchService(session, SemanticFakeProvider()).search(owner.id, "related concept", mode="semantic")
    assert response.total == 1 and response.items[0].paper.id == visible.id


@pytest.mark.asyncio
async def test_semantic_empty_and_entity_pagination(session: AsyncSession) -> None:
    owner = await make_user(session, "semantic-page-owner")
    assert (await SearchService(session, SemanticFakeProvider()).search(owner.id, "nothing ready", mode="semantic")).total == 0
    for index in range(3):
        await add_paper_chunk(session, owner, f"Paper {index}", f"concept {index}", vector(0, index * 0.05))
    await session.commit()
    first = await SearchService(session, SemanticFakeProvider()).search(owner.id, "same idea", page=1, page_size=2, mode="semantic")
    second = await SearchService(session, SemanticFakeProvider()).search(owner.id, "same idea", page=2, page_size=2, mode="semantic")
    assert first.total == second.total == 3
    assert {item.paper.id for item in first.items}.isdisjoint(item.paper.id for item in second.items)


@pytest.mark.asyncio
async def test_semantic_query_provider_errors_are_explicit(session: AsyncSession) -> None:
    owner = await make_user(session, "semantic-error-owner")
    wrong = SemanticFakeProvider()
    wrong.dimension = 768
    with pytest.raises(SemanticRetrievalError, match="dimension"):
        await SearchService(session, wrong).search(owner.id, "query text", mode="semantic")
    with pytest.raises(SemanticRetrievalError, match="unavailable"):
        await SearchService(session, SemanticFakeProvider(fail=True)).search(owner.id, "query text", mode="semantic")
