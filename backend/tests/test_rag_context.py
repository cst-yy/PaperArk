import hashlib
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Note, Paper, Section, User
from app.schemas.rag import RAGContextRequest
from app.services.rag_context import RAGCandidate, RAGContextAssembler
from app.services.rag_retrieval import RAGRetrievalService
from app.services.rag_service import RAGService
from tests.test_semantic_search import SemanticFakeProvider, vector


def chunk_candidate(index: int, content: str, *, section_id: uuid.UUID | None = None,
                    document_id: uuid.UUID | None = None, paper_id: uuid.UUID | None = None) -> RAGCandidate:
    return RAGCandidate(source_key=f"chunk:{index}", source_type="paper_chunk", title="Paper",
        paper_title="Paper", content=content, paper_id=paper_id or uuid.UUID(int=1),
        document_id=document_id or uuid.UUID(int=2), section_id=section_id or uuid.UUID(int=3),
        section_title="Method", page_start=index + 1, page_end=index + 1, chunk_index=index,
        retrieval_score=1 - index * 0.01)


def test_assembler_merges_adjacent_deduplicates_and_never_crosses_section() -> None:
    section_a, section_b = uuid.uuid4(), uuid.uuid4()
    candidates = [
        chunk_candidate(0, "alpha beta shared", section_id=section_a),
        chunk_candidate(1, "shared gamma delta", section_id=section_a),
        chunk_candidate(2, "different section", section_id=section_b),
        chunk_candidate(9, "alpha beta shared", section_id=section_a),
    ]
    sources, context, _, _ = RAGContextAssembler().assemble(candidates, max_sources=8, token_budget=6000)
    assert sources[0].source_key.startswith("chunk_window:")
    assert sources[0].page_start == 1 and sources[0].page_end == 2
    assert len(sources) == 2 and sources[1].section_id == section_b
    assert "[SOURCE 1 | PAPER]" in context and "Pages: 1-2" in context


def test_assembler_budget_caps_notes_and_is_deterministic() -> None:
    candidates = [chunk_candidate(10, "x" * 5000, section_id=uuid.uuid4())]
    candidates += [RAGCandidate(source_key=f"note:{i}", source_type="note", title=f"Note {i}",
        content="n" * 2000, note_id=uuid.UUID(int=20 + i), retrieval_score=.8 - i * .1) for i in range(4)]
    assembler = RAGContextAssembler()
    first = assembler.assemble(candidates, max_sources=8, token_budget=1300)
    second = assembler.assemble(candidates, max_sources=8, token_budget=1300)
    sources, context, tokens, truncated = first
    assert sum(source.source_type == "note" for source in sources) <= 2
    assert tokens <= 1300 and truncated
    assert any(source.truncated for source in sources)
    assert hashlib.sha256(context.encode()).hexdigest() == hashlib.sha256(second[1].encode()).hexdigest()


def test_source_level_rrf_preserves_union_and_reinforces_shared_source() -> None:
    a, b, c = chunk_candidate(1, "A"), chunk_candidate(2, "B"), chunk_candidate(3, "C")
    lexical = [a, b]
    semantic = [c, b]
    fused = RAGRetrievalService.fuse(lexical, semantic)
    assert fused[0].source_key == b.source_key
    assert {item.source_key for item in fused} == {a.source_key, b.source_key, c.source_key}
    assert fused[0].retrieval_method == "hybrid"


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(user)
    await session.flush()
    return user


async def add_paper(session: AsyncSession, user: User, title: str, token: str, axis: int):
    paper = Paper(user_id=user.id, title=title, status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=f"pdfs/{paper.id}.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    section = Section(document_id=document.id, title="Method", order_index=0)
    session.add(section)
    await session.flush()
    chunk = Chunk(document_id=document.id, section_id=section.id, chunk_index=0,
        content=f"{token} paper evidence", page_start=4, page_end=4, embedding=vector(axis),
        embedding_status="ready", embedding_model="semantic-fake-v1", embedding_dimension=384,
        embedding_content_hash="x")
    session.add(chunk)
    await session.flush()
    return paper, chunk


@pytest.mark.asyncio
async def test_paper_scope_and_user_scope_apply_to_chunks_and_notes(session: AsyncSession) -> None:
    owner = await make_user(session, "rag-owner")
    foreign = await make_user(session, "rag-foreign")
    paper_a, _ = await add_paper(session, owner, "Paper A", "ragscopeterm", 0)
    paper_b, _ = await add_paper(session, owner, "Paper B", "ragscopeterm", 0)
    await add_paper(session, foreign, "Foreign", "ragscopeterm", 0)
    paper_note = Note(user_id=owner.id, paper_id=paper_a.id, note_type="paper", title="Scoped note", content_markdown="ragscopeterm interpretation")
    general_note = Note(user_id=owner.id, note_type="general", title="General", content_markdown="ragscopeterm general")
    session.add_all([paper_note, general_note])
    await session.commit()
    candidates = await RAGRetrievalService(session, SemanticFakeProvider()).lexical(owner.id, "ragscopeterm", paper_a.id)
    assert candidates
    assert all(item.paper_id == paper_a.id for item in candidates)
    assert {item.note_id for item in candidates if item.source_type == "note"} == {paper_note.id}
    assert all(item.paper_id != paper_b.id for item in candidates)


@pytest.mark.asyncio
async def test_rag_service_empty_and_hybrid_degradation_without_llm(session: AsyncSession) -> None:
    owner = await make_user(session, "rag-empty")
    empty = await RAGService(session, SemanticFakeProvider()).build_context(owner.id,
        RAGContextRequest(query="nothing exists", mode="lexical"))
    assert empty.sources == [] and empty.context_text == "" and empty.estimated_tokens == 0
    await add_paper(session, owner, "Degrade", "degradeterm", 0)
    await session.commit()
    degraded = await RAGService(session, SemanticFakeProvider(fail=True)).build_context(owner.id,
        RAGContextRequest(query="degradeterm", mode="hybrid"))
    assert degraded.sources and degraded.effective_mode == "lexical" and degraded.degraded
    assert degraded.semantic_available is False
