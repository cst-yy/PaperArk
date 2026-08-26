import uuid

import pytest

from app.models import Author, Folder, Keyword, Note, Paper, PaperAuthor, PaperFolder, PaperKeyword, PaperTag, Tag, User
from app.services.paper_list_service import PaperListService


async def _user(session, suffix: str):
    user = User(id=uuid.uuid4(), username=f"paper-list-{suffix}", email=f"paper-list-{suffix}@example.com", password_hash="")
    session.add(user)
    await session.flush()
    return user.id


def _query(**overrides):
    values = dict(q=None, year_from=None, year_to=None, journal=None, author=None, tag_id=None, keyword=None,
                  reading_status=None, starred=None, sort="updated_at", order="desc", page=1, page_size=25)
    values.update(overrides)
    return values


@pytest.mark.asyncio
async def test_paper_list_is_paper_level_searchable_sorted_and_user_scoped(session):
    owner = await _user(session, "owner")
    foreign_user = await _user(session, "foreign")
    first = Paper(user_id=owner, title="Federated Systems", title_zh="联邦系统", journal="IEEE", publication_year=2025, citation_text="Yang et al. 2025")
    second = Paper(user_id=owner, title="Another Paper", publication_year=2024)
    foreign = Paper(user_id=foreign_user, title="Federated Foreign", publication_year=2026)
    session.add_all([first, second, foreign])
    await session.flush()
    author_a = Author(name="Yu Yang")
    author_b = Author(name="Suxia Zhu")
    tag = Tag(user_id=owner, name="Federated Learning", normalized_name="federated learning")
    keyword = Keyword(user_id=owner, display_name="heterogeneity", normalized_name="heterogeneity")
    folder = Folder(user_id=owner, name="Core")
    session.add_all([author_a, author_b, tag, keyword, folder])
    await session.flush()
    session.add_all([
        PaperAuthor(paper_id=first.id, author_id=author_a.id, author_order=0),
        PaperAuthor(paper_id=first.id, author_id=author_b.id, author_order=1),
        PaperTag(paper_id=first.id, tag_id=tag.id),
        PaperKeyword(paper_id=first.id, keyword_id=keyword.id, source="manual"),
        PaperFolder(paper_id=first.id, folder_id=folder.id),
        Note(user_id=owner, paper_id=first.id, title="Experiment notes", note_type="paper"),
    ])
    await session.flush()
    service = PaperListService(session)

    by_author = await service.list_rows(owner, **_query(q="Yu Yang"))
    assert by_author.total == 1 and [item.id for item in by_author.items] == [first.id]
    assert len(by_author.items[0].authors) == 2 and by_author.items[0].note_count == 1
    for term in ["联邦系统", "IEEE", "2025", "Yang et al.", "heterogeneity", "Federated Learning", "Core", "Experiment notes"]:
        result = await service.list_rows(owner, **_query(q=term))
        assert result.total == 1 and result.items[0].id == first.id
    sorted_page = await service.list_rows(owner, **_query(sort="publication_year", order="desc"))
    assert [item.id for item in sorted_page.items] == [first.id, second.id]
    assert sorted_page.total == 2


@pytest.mark.asyncio
async def test_paper_list_filters_and_counts_papers_not_relations(session):
    owner = await _user(session, "filters")
    papers = [Paper(user_id=owner, title=f"Paper {index}", publication_year=2020 + index, reading_status="reading" if index % 2 else "unread") for index in range(4)]
    session.add_all(papers)
    await session.flush()
    service = PaperListService(session)
    result = await service.list_rows(owner, **_query(year_from=2021, year_to=2023, sort="publication_year", order="asc"))
    assert result.total == 3
    assert [item.publication_year for item in result.items] == [2021, 2022, 2023]
    reading = await service.list_rows(owner, **_query(reading_status="reading"))
    assert reading.total == 2
