"""S8-A unified search contract, aggregation, pagination, and isolation tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Author, Chunk, Document, DocumentElement, Keyword, Paper, PaperAuthor,
    PaperKeyword, PaperTag, Reference, Section, Tag, User,
)
from app.services.search_service import MAX_MATCHES, SearchService
from app.services.search_query import QueryNormalizer, build_snippet


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_search_covers_metadata_and_every_document_source(session: AsyncSession) -> None:
    user = await make_user(session, "source-owner")
    paper = Paper(user_id=user.id, title="TitleUnique study", abstract="AbstractUnique evidence", status="ready")
    session.add(paper)
    await session.flush()
    author = Author(name="AuthorUnique Person")
    tag = Tag(user_id=user.id, name="TagUnique", normalized_name="tagunique")
    keyword = Keyword(user_id=user.id, display_name="KeywordUnique", normalized_name="keywordunique")
    session.add_all([author, tag, keyword])
    await session.flush()
    session.add_all([PaperAuthor(paper_id=paper.id, author_id=author.id), PaperTag(paper_id=paper.id, tag_id=tag.id), PaperKeyword(paper_id=paper.id, keyword_id=keyword.id, source="manual")])
    document = Document(paper_id=paper.id, file_path="pdfs/sources.pdf", parse_status="ready", page_count=8)
    session.add(document)
    await session.flush()
    section = Section(document_id=document.id, title="SectionUnique experiments", order_index=0, page_start=2, page_end=5)
    session.add(section)
    await session.flush()
    session.add_all([
        Chunk(document_id=document.id, section_id=section.id, chunk_index=0, content="ChunkUnique full text", page_start=3, page_end=3),
        Reference(document_id=document.id, section_id=None, order_index=0, raw_text="ReferenceUnique cited work", title="ReferenceUnique", page_start=6, page_end=6),
        DocumentElement(document_id=document.id, section_id=section.id, order_index=0, element_type="figure", page_number=4, caption="FigureUnique caption"),
        DocumentElement(document_id=document.id, section_id=section.id, order_index=1, element_type="table", page_number=5, caption="TableUnique caption"),
    ])
    await session.commit()

    cases = {"TitleUnique": "title", "AuthorUnique": "author", "TagUnique": "tag", "KeywordUnique": "keyword", "SectionUnique": "section", "ChunkUnique": "chunk", "ReferenceUnique": "reference", "FigureUnique": "figure", "TableUnique": "table"}
    for query, source in cases.items():
        response = await SearchService(session).search(user.id, query)
        assert response.total == 1
        assert response.items[0].paper.id == paper.id
        assert source in {match.source for match in response.items[0].matches}
    chunk_result = (await SearchService(session).search(user.id, "ChunkUnique")).items[0]
    assert chunk_result.matches[0].document_id == document.id
    assert chunk_result.matches[0].page_start == 3


@pytest.mark.asyncio
async def test_search_aggregates_relation_explosion_to_one_paper(session: AsyncSession) -> None:
    user = await make_user(session, "explosion-owner")
    paper = Paper(user_id=user.id, title="shared aggregation", status="ready")
    session.add(paper)
    await session.flush()
    for index in range(3):
        author = Author(name=f"shared author {index}")
        session.add(author)
        await session.flush()
        session.add(PaperAuthor(paper_id=paper.id, author_id=author.id, author_order=index))
    for index in range(4):
        tag = Tag(user_id=user.id, name=f"shared tag {index}", normalized_name=f"shared tag {index}")
        session.add(tag)
        await session.flush()
        session.add(PaperTag(paper_id=paper.id, tag_id=tag.id))
    for index in range(5):
        keyword = Keyword(user_id=user.id, display_name=f"shared keyword {index}", normalized_name=f"shared keyword {index}")
        session.add(keyword)
        await session.flush()
        session.add(PaperKeyword(paper_id=paper.id, keyword_id=keyword.id, source="manual"))
    document = Document(paper_id=paper.id, file_path="pdfs/explosion.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    session.add_all([Chunk(document_id=document.id, chunk_index=index, content=f"shared chunk {index}", page_start=index + 1, page_end=index + 1) for index in range(20)])
    session.add_all([Reference(document_id=document.id, order_index=index, raw_text=f"shared reference {index}", page_start=1, page_end=1) for index in range(10)])
    await session.commit()

    response = await SearchService(session).search(user.id, "shared")

    assert response.total == 1
    assert len(response.items) == 1
    assert response.items[0].match_count == 43
    assert len(response.items[0].matches) == MAX_MATCHES


@pytest.mark.asyncio
async def test_search_paginates_after_paper_aggregation(session: AsyncSession) -> None:
    user = await make_user(session, "page-owner")
    for paper_index in range(10):
        paper = Paper(user_id=user.id, title=f"paginationterm paper {paper_index:02d}", status="ready")
        session.add(paper)
        await session.flush()
        document = Document(paper_id=paper.id, file_path=f"pdfs/page-{paper_index}.pdf", parse_status="ready")
        session.add(document)
        await session.flush()
        session.add_all([Chunk(document_id=document.id, chunk_index=chunk_index, content=f"paginationterm body {chunk_index}") for chunk_index in range(4)])
    await session.commit()

    first = await SearchService(session).search(user.id, "paginationterm", page=1, page_size=5)
    second = await SearchService(session).search(user.id, "paginationterm", page=2, page_size=5)

    assert first.total == second.total == 10
    assert len(first.items) == len(second.items) == 5
    assert {item.paper.id for item in first.items}.isdisjoint(item.paper.id for item in second.items)


@pytest.mark.asyncio
async def test_search_isolates_all_derived_sources_by_user(session: AsyncSession) -> None:
    owner = await make_user(session, "isolation-owner")
    other = await make_user(session, "isolation-other")
    for user, title in [(owner, "Visible"), (other, "Foreign")]:
        paper = Paper(user_id=user.id, title=title, status="ready")
        session.add(paper)
        await session.flush()
        document = Document(paper_id=paper.id, file_path=f"pdfs/{title}.pdf", parse_status="ready")
        session.add(document)
        await session.flush()
        section = Section(document_id=document.id, title="isolatedtoken section", order_index=0, page_start=1, page_end=1)
        session.add(section)
        await session.flush()
        session.add_all([
            Chunk(document_id=document.id, section_id=section.id, chunk_index=0, content="isolatedtoken chunk"),
            Reference(document_id=document.id, order_index=0, raw_text="isolatedtoken reference", page_start=1, page_end=1),
            DocumentElement(document_id=document.id, order_index=0, element_type="figure", page_number=1, caption="isolatedtoken figure"),
        ])
    await session.commit()

    response = await SearchService(session).search(owner.id, "isolatedtoken")

    assert response.total == 1
    assert response.items[0].paper.title == "Visible"


def test_query_normalization_and_plain_text_snippet() -> None:
    doi = QueryNormalizer.normalize("  https://doi.org/10.1016/J.NEUCOM.2025.01  ")
    arxiv = QueryNormalizer.normalize(" arXiv:2401.12345v2 ")
    assert doi.normalized == "10.1016/j.neucom.2025.01" and doi.looks_like_doi
    assert arxiv.normalized == "2401.12345v2" and arxiv.looks_like_arxiv
    text = "prefix " * 80 + "federated optimization under severe non-IID settings" + " suffix" * 80
    snippet = build_snippet(text, QueryNormalizer.normalize("federated optimization"))
    assert len(snippet) <= 242
    assert "federated optimization" in snippet
    assert "<mark>" not in snippet and snippet.startswith("…") and snippet.endswith("…")


@pytest.mark.asyncio
async def test_metadata_fuzzy_and_identifier_shortcuts(session: AsyncSession) -> None:
    user = await make_user(session, "quality-owner")
    exact = Paper(user_id=user.id, title="Federated Representation Learning", doi="10.5555/Quality.Test", arxiv_id="2401.12345", status="ready")
    noise = Paper(user_id=user.id, title="Unrelated paper", abstract="10.5555/quality.test only in abstract", status="ready")
    session.add_all([exact, noise])
    await session.commit()

    fuzzy = await SearchService(session).search(user.id, "Federatd Representation")
    doi = await SearchService(session).search(user.id, "https://doi.org/10.5555/QUALITY.TEST")
    arxiv = await SearchService(session).search(user.id, "arXiv:2401.12345")

    assert fuzzy.items[0].paper.id == exact.id
    assert doi.total == 1 and doi.items[0].paper.id == exact.id and doi.items[0].matches[0].source == "doi"
    assert arxiv.total == 1 and arxiv.items[0].matches[0].source == "arxiv"


@pytest.mark.asyncio
async def test_fulltext_uses_and_like_websearch_semantics(session: AsyncSession) -> None:
    user = await make_user(session, "fts-owner")
    both = Paper(user_id=user.id, title="Both", status="ready")
    partial = Paper(user_id=user.id, title="Partial", status="ready")
    session.add_all([both, partial])
    await session.flush()
    both_doc = Document(paper_id=both.id, file_path="pdfs/both.pdf", parse_status="ready")
    partial_doc = Document(paper_id=partial.id, file_path="pdfs/partial.pdf", parse_status="ready")
    session.add_all([both_doc, partial_doc])
    await session.flush()
    session.add_all([
        Chunk(document_id=both_doc.id, chunk_index=0, content="federated optimization is robust"),
        Chunk(document_id=partial_doc.id, chunk_index=0, content="federated systems only"),
        Section(document_id=both_doc.id, title="Optimization", content="federated learning", order_index=0),
        Reference(document_id=both_doc.id, order_index=0, title="Federated Optimization", raw_text="Federated Optimization", page_start=1, page_end=1),
    ])
    await session.commit()

    result = await SearchService(session).search(user.id, "federated optimization")
    assert result.total == 1 and result.items[0].paper.id == both.id
    assert {match.source for match in result.items[0].matches} >= {"chunk", "section", "reference"}


@pytest.mark.asyncio
async def test_long_paper_weak_hits_do_not_beat_exact_title(session: AsyncSession) -> None:
    user = await make_user(session, "ranking-owner")
    exact = Paper(user_id=user.id, title="rare ranking phrase", status="ready")
    long = Paper(user_id=user.id, title="Long survey", status="ready")
    session.add_all([exact, long])
    await session.flush()
    document = Document(paper_id=long.id, file_path="pdfs/long.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    session.add_all([Chunk(document_id=document.id, chunk_index=index, content=f"rare ranking phrase context {index}") for index in range(100)])
    await session.commit()

    result = await SearchService(session).search(user.id, "rare ranking phrase")
    assert result.items[0].paper.id == exact.id
    assert result.items[1].match_count == 100


@pytest.mark.asyncio
async def test_one_character_query_is_rejected(session: AsyncSession) -> None:
    user = await make_user(session, "short-owner")
    session.add(Paper(user_id=user.id, title="A", status="ready"))
    await session.commit()
    assert (await SearchService(session).search(user.id, "a")).total == 0
