import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Note, Paper, User
from app.schemas.search import (SearchMatchResponse, SearchNoteBrief, SearchNoteResult,
    SearchPaperBrief, SearchPaperResult)
from app.services.hybrid_search import entity_key, materialize_fusion, rrf_fuse
from app.services.search_service import SearchService
from tests.test_semantic_search import SemanticFakeProvider, vector


def paper_result(identifier: uuid.UUID, title: str) -> SearchPaperResult:
    return SearchPaperResult(paper=SearchPaperBrief(id=identifier, title=title), score=1,
        match_count=1, matches=[SearchMatchResponse(source="title", text=title)])


def note_result(identifier: uuid.UUID, title: str) -> SearchNoteResult:
    return SearchNoteResult(note=SearchNoteBrief(id=identifier, title=title, note_type="general"),
        score=1, match_count=1, matches=[SearchMatchResponse(source="note_content", text=title)])


def test_rrf_is_entity_union_reinforces_both_and_is_deterministic() -> None:
    a, b, c, d = [uuid.UUID(int=value) for value in range(1, 5)]
    lexical = [paper_result(a, "A"), note_result(b, "B"), paper_result(c, "C")]
    semantic = [paper_result(c, "C"), paper_result(a, "A"), note_result(d, "D")]
    first = rrf_fuse(lexical, semantic)
    second = rrf_fuse(lexical, semantic)
    assert [item.entity_key for item in first] == [item.entity_key for item in second]
    assert first[0].entity_key == ("paper", a)
    assert {item.entity_key for item in first} == {
        ("paper", a), ("note", b), ("paper", c), ("note", d)}
    assert first[0].lexical_rank == 1 and first[0].semantic_rank == 2


def test_hybrid_merge_deduplicates_same_match() -> None:
    identifier = uuid.uuid4()
    lexical = paper_result(identifier, "same chunk")
    lexical.matches = [SearchMatchResponse(source="chunk", text="same body",
        document_id=uuid.UUID(int=10), page_start=4)]
    semantic = paper_result(identifier, "same chunk")
    semantic.matches = [SearchMatchResponse(source="chunk", text="same body",
        document_id=uuid.UUID(int=10), page_start=4)]
    result = materialize_fusion([lexical], [semantic])[0]
    assert result.match_count == 1 and len(result.matches) == 1


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(user)
    await session.flush()
    return user


async def add_entity(session: AsyncSession, user: User, title: str, content: str,
                     embedding: list[float]) -> Paper:
    paper = Paper(user_id=user.id, title=title, status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=f"pdfs/{paper.id}.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    session.add(Chunk(document_id=document.id, chunk_index=0, content=content,
        embedding=embedding, embedding_status="ready", embedding_model="semantic-fake-v1",
        embedding_dimension=384, embedding_content_hash="x"))
    return paper


@pytest.mark.asyncio
async def test_hybrid_unions_single_chain_entities_and_reinforces_both(session: AsyncSession) -> None:
    owner = await make_user(session, "hybrid-owner")
    lexical_only = await add_entity(session, owner, "fusiontoken lexical", "unrelated", vector(1))
    semantic_only = await add_entity(session, owner, "No literal overlap", "semantic idea", vector(0))
    both = await add_entity(session, owner, "fusiontoken reinforced", "semantic reinforced", vector(0, 0.05))
    note = Note(user_id=owner.id, note_type="general", title="Semantic-only note",
        content_markdown="user interpretation", embedding=vector(0, 0.1),
        embedding_status="ready", embedding_model="semantic-fake-v1",
        embedding_dimension=384, embedding_content_hash="n")
    session.add(note)
    await session.commit()

    response = await SearchService(session, SemanticFakeProvider()).search(
        owner.id, "fusiontoken", mode="hybrid")
    keys = [entity_key(item) for item in response.items]
    assert keys[0] == ("paper", both.id)
    assert ("paper", lexical_only.id) in keys
    assert ("paper", semantic_only.id) in keys
    assert ("note", note.id) in keys
    assert response.retrieval.effective_mode == "hybrid"
    assert response.retrieval.semantic_available is True
    first = await SearchService(session, SemanticFakeProvider()).search(owner.id, "fusiontoken", page=1, page_size=2, mode="hybrid")
    second = await SearchService(session, SemanticFakeProvider()).search(owner.id, "fusiontoken", page=2, page_size=2, mode="hybrid")
    assert first.total == second.total == 4
    assert {entity_key(item) for item in first.items}.isdisjoint(entity_key(item) for item in second.items)


@pytest.mark.asyncio
async def test_hybrid_semantic_failure_explicitly_degrades_to_lexical(session: AsyncSession) -> None:
    owner = await make_user(session, "hybrid-degraded")
    paper = await add_entity(session, owner, "degradetoken paper", "body", vector(0))
    await session.commit()
    response = await SearchService(session, SemanticFakeProvider(fail=True)).search(
        owner.id, "degradetoken", mode="hybrid")
    assert response.total == 1 and response.items[0].paper.id == paper.id
    assert response.retrieval.requested_mode == "hybrid"
    assert response.retrieval.effective_mode == "lexical"
    assert response.retrieval.semantic_available is False
