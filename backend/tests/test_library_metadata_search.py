import uuid

import pytest

from app.models import Author, Folder, Keyword, Paper, PaperAuthor, PaperFolder, PaperKeyword, PaperTag, Tag, User
from app.repositories.paper_repository import PaperRepository


async def create_user(session, suffix: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username=f"library-{suffix}", email=f"library-{suffix}@example.com", password_hash=""))
    await session.flush()
    return user_id


@pytest.mark.asyncio
async def test_library_metadata_search_matches_each_supported_field_once(session):
    user_id = await create_user(session, "search")
    paper = Paper(
        id=uuid.uuid4(), user_id=user_id, title="Representation Study",
        abstract="Study of robust optimization", doi="10.1000/metadata",
        arxiv_id="2401.01234", journal="Neurocomputing", conference="NeurIPS",
        publisher="Academic Press", publication_year=2025, status="ready", is_starred=True,
    )
    author = Author(id=uuid.uuid4(), name="Ada Lovelace")
    second_author = Author(id=uuid.uuid4(), name="Grace Hopper")
    tag = Tag(id=uuid.uuid4(), user_id=user_id, name="Important", normalized_name="important")
    second_tag = Tag(id=uuid.uuid4(), user_id=user_id, name="Research", normalized_name="research")
    folder = Folder(id=uuid.uuid4(), user_id=user_id, name="Reading")
    keyword = Keyword(id=uuid.uuid4(), user_id=user_id, display_name="Federated Learning", normalized_name="federated learning")
    second_keyword = Keyword(id=uuid.uuid4(), user_id=user_id, display_name="Optimization", normalized_name="optimization")
    session.add_all([paper, author, second_author, tag, second_tag, folder, keyword, second_keyword])
    await session.flush()
    session.add_all([
        PaperAuthor(paper_id=paper.id, author_id=author.id, author_order=0),
        PaperAuthor(paper_id=paper.id, author_id=second_author.id, author_order=1),
        PaperTag(paper_id=paper.id, tag_id=tag.id),
        PaperTag(paper_id=paper.id, tag_id=second_tag.id),
        PaperFolder(paper_id=paper.id, folder_id=folder.id),
        PaperKeyword(paper_id=paper.id, keyword_id=keyword.id, source="manual"),
        PaperKeyword(paper_id=paper.id, keyword_id=keyword.id, source="ai"),
        PaperKeyword(paper_id=paper.id, keyword_id=second_keyword.id, source="manual"),
    ])
    await session.flush()
    repo = PaperRepository(session)

    for query in ["Representation", "robust", "Ada", "Important", "Federated", "10.1000", "2401.01234", "Neuro", "NeurIPS", "Academic"]:
        result = await repo.list_papers(user_id=user_id, q=query)
        assert [item.id for item in result.items] == [paper.id]
        assert result.total == 1

    combined = await repo.list_papers(user_id=user_id, q="Federated", tag_id=tag.id, folder_id=folder.id, year=2025, starred=True, status="ready")
    assert combined.total == 1
    assert [item.id for item in combined.items] == [paper.id]


@pytest.mark.asyncio
async def test_library_reading_status_filter_is_user_scoped_and_composes_with_processing_status(session):
    user_id = await create_user(session, "reading-status-owner")
    other_id = await create_user(session, "reading-status-other")
    matching = Paper(id=uuid.uuid4(), user_id=user_id, title="Reading", status="ready", reading_status="reading")
    wrong_processing = Paper(id=uuid.uuid4(), user_id=user_id, title="Not ready", status="imported", reading_status="reading")
    wrong_reading = Paper(id=uuid.uuid4(), user_id=user_id, title="Finished", status="ready", reading_status="finished")
    foreign = Paper(id=uuid.uuid4(), user_id=other_id, title="Foreign", status="ready", reading_status="reading")
    session.add_all([matching, wrong_processing, wrong_reading, foreign])
    await session.flush()

    result = await PaperRepository(session).list_papers(
        user_id=user_id,
        status="ready",
        reading_status="reading",
    )

    assert result.total == 1
    assert [paper.id for paper in result.items] == [matching.id]


@pytest.mark.asyncio
async def test_library_metadata_search_is_user_scoped_and_pagination_counts_papers(session):
    user_id = await create_user(session, "owner")
    other_id = await create_user(session, "other")
    owner_paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Owner paper")
    other_paper = Paper(id=uuid.uuid4(), user_id=other_id, title="Other paper")
    owner_keyword = Keyword(id=uuid.uuid4(), user_id=user_id, display_name="Shared Phrase", normalized_name="shared phrase")
    other_keyword = Keyword(id=uuid.uuid4(), user_id=other_id, display_name="Foreign Only", normalized_name="foreign only")
    session.add_all([owner_paper, other_paper, owner_keyword, other_keyword])
    await session.flush()
    session.add_all([
        PaperKeyword(paper_id=owner_paper.id, keyword_id=owner_keyword.id, source="manual"),
        PaperKeyword(paper_id=other_paper.id, keyword_id=other_keyword.id, source="manual"),
    ])
    await session.flush()
    repo = PaperRepository(session)

    shared = await repo.list_papers(user_id=user_id, q="Shared", limit=1)
    assert shared.total == 1
    assert [item.id for item in shared.items] == [owner_paper.id]
    assert (await repo.list_papers(user_id=user_id, q="Foreign Only")).total == 0
    assert (await repo.list_papers(user_id=user_id, q="   ")).total == 1
