import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Note, Paper, Section, User
from app.services.embedding_service import (EmbeddingLifecycleService,
    build_chunk_embedding_text, build_note_embedding_text, embedding_content_hash)


class FakeProvider:
    model_name = "fake-embedding-v1"
    dimension = 384

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[list[str]] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self.fail:
            raise RuntimeError("fake provider unavailable")
        return [[float((index + 1) % 7)] * self.dimension for index, _ in enumerate(texts)]


async def fixture_data(session: AsyncSession, name: str = "embed-owner"):
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Embedding paper", status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=f"pdfs/{name}.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    section = Section(document_id=document.id, title="Experiments", order_index=0)
    session.add(section)
    await session.flush()
    chunks = [Chunk(document_id=document.id, section_id=section.id, chunk_index=i, content=f"chunk body {i}") for i in range(3)]
    note = Note(user_id=user.id, paper_id=paper.id, note_type="paper", title="My note", content_markdown="## Idea\n**interpretation**")
    session.add_all([*chunks, note])
    await session.commit()
    return user, chunks, note


@pytest.mark.asyncio
async def test_embedding_batch_hash_and_unchanged_skip(session: AsyncSession) -> None:
    user, chunks, note = await fixture_data(session)
    provider = FakeProvider()
    service = EmbeddingLifecycleService(session, provider, batch_size=2)
    first = await service.rebuild(user.id)
    second = await service.rebuild(user.id)

    assert first.processed == 4 and first.failed == 0
    assert [len(batch) for batch in provider.calls] == [2, 2]
    assert second.skipped == 4 and len(provider.calls) == 2
    assert all(chunk.embedding_status == "ready" for chunk in chunks)
    assert note.embedding_model == provider.model_name and note.embedding_dimension == 384
    assert chunks[0].embedding_content_hash == embedding_content_hash(build_chunk_embedding_text(chunks[0], "Experiments"))
    assert note.embedding_content_hash == embedding_content_hash(build_note_embedding_text(note))


@pytest.mark.asyncio
async def test_changed_note_reembeds_without_touching_primary_data(session: AsyncSession) -> None:
    user, _, note = await fixture_data(session, "embed-change")
    provider = FakeProvider()
    service = EmbeddingLifecycleService(session, provider)
    await service.rebuild(user.id)
    old_hash = note.embedding_content_hash
    note.content_markdown = "new user interpretation"
    note.embedding_status = "pending"
    await session.commit()
    result = await service.rebuild(user.id)
    assert result.processed == 1 and result.skipped == 3
    assert note.embedding_content_hash != old_hash
    assert note.content_markdown == "new user interpretation"


@pytest.mark.asyncio
async def test_failure_and_status_are_user_scoped(session: AsyncSession) -> None:
    owner, _, note = await fixture_data(session, "embed-failure")
    other, _, other_note = await fixture_data(session, "embed-other")
    service = EmbeddingLifecycleService(session, FakeProvider(fail=True), batch_size=8)
    result = await service.rebuild(owner.id)
    status = await service.status(owner.id)
    assert result.failed == 4 and note.embedding_status == "failed"
    assert "fake provider unavailable" in note.embedding_error
    assert status["chunk"]["failed"] == 3 and status["note"]["failed"] == 1
    assert other_note.embedding_status == "pending"
    assert (await service.status(other.id))["note"]["pending"] == 1
