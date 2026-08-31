import uuid

import pytest

from app.models import Author, Paper, PaperAuthor, ResearchIdentity, User
from app.api.endpoints.research_identity import get_identity
from app.repositories.paper_repository import PaperRepository
from app.services.paper_service import PaperMapper
from app.schemas.research_identity import ResearchIdentityUpdate


@pytest.mark.asyncio
async def test_my_papers_includes_every_signature_position_and_role_filters_overlap(session):
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username="identity-owner", email="identity@example.com", password_hash=""))
    me, other = Author(name="Yang Yu"), Author(name="Yang Yu")
    session.add_all([me, other]); await session.flush()
    first = Paper(user_id=user_id, title="First and corresponding")
    second = Paper(user_id=user_id, title="Second author")
    co_first = Paper(user_id=user_id, title="Co-first")
    foreign_name = Paper(user_id=user_id, title="Same name, different Author ID")
    session.add_all([first, second, co_first, foreign_name]); await session.flush()
    session.add_all([
        PaperAuthor(paper_id=first.id, author_id=me.id, author_order=0, is_corresponding=True),
        PaperAuthor(paper_id=second.id, author_id=me.id, author_order=1),
        PaperAuthor(paper_id=co_first.id, author_id=me.id, author_order=2, is_co_first=True),
        PaperAuthor(paper_id=foreign_name.id, author_id=other.id, author_order=0),
    ]); await session.flush()
    repo = PaperRepository(session)

    all_mine = await repo.list_papers(user_id, identity_author_id=me.id)
    assert {paper.id for paper in all_mine.items} == {first.id, second.id, co_first.id}
    assert (await repo.list_papers(user_id, identity_author_id=me.id, author_role="first")).total == 2
    assert [paper.id for paper in (await repo.list_papers(user_id, identity_author_id=me.id, author_role="corresponding")).items] == [first.id]
    assert [paper.id for paper in (await repo.list_papers(user_id, identity_author_id=me.id, author_role="other")).items] == [second.id]

    mapped = PaperMapper.to_list_response(next(paper for paper in all_mine.items if paper.id == first.id), me.id)
    assert mapped.my_author_roles is not None
    assert mapped.my_author_roles.is_first_author is True
    assert mapped.my_author_roles.is_corresponding is True


@pytest.mark.asyncio
async def test_my_papers_never_crosses_paper_owner_scope(session):
    owner_id, foreign_id = uuid.uuid4(), uuid.uuid4()
    session.add_all([
        User(id=owner_id, username="identity-a", email="identity-a@example.com", password_hash=""),
        User(id=foreign_id, username="identity-b", email="identity-b@example.com", password_hash=""),
    ])
    me = Author(name="Unique Me"); session.add(me); await session.flush()
    owned = Paper(user_id=owner_id, title="Owned")
    foreign = Paper(user_id=foreign_id, title="Foreign")
    session.add_all([owned, foreign]); await session.flush()
    session.add_all([
        PaperAuthor(paper_id=owned.id, author_id=me.id, author_order=3),
        PaperAuthor(paper_id=foreign.id, author_id=me.id, author_order=0),
    ]); await session.flush()
    result = await PaperRepository(session).list_papers(owner_id, identity_author_id=me.id)
    assert [paper.id for paper in result.items] == [owned.id]


def test_research_identity_optional_metadata_is_normalized_without_affiliation_binding():
    author_id = uuid.uuid4()
    value = ResearchIdentityUpdate(author_id=author_id, orcid="https://orcid.org/0000-0002-1825-0097", email="  ME@Example.EDU ")
    assert value.orcid == "0000-0002-1825-0097"
    assert value.email == "me@example.edu"
    assert ResearchIdentityUpdate(author_id=author_id).orcid is None
    assert "affiliation" not in ResearchIdentityUpdate.model_fields


@pytest.mark.asyncio
async def test_get_research_identity_eager_loads_author_for_async_response(session):
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username="identity-get", email="identity-get@example.com", password_hash=""))
    author = Author(name="Saved Researcher")
    session.add(author)
    await session.flush()
    session.add(ResearchIdentity(user_id=user_id, author_id=author.id, display_name="Saved Researcher"))
    await session.flush()
    session.expire_all()

    response = await get_identity(db=session, user_id=user_id)

    assert response is not None
    assert response.author_id == author.id
    assert response.author_name == "Saved Researcher"
