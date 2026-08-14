import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (Note, Paper, ResearchContribution, ResearchExperiment,
    ResearchNoteProfile, User)
from app.services.search_service import SearchService


async def user(session: AsyncSession, name: str) -> User:
    value = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(value)
    await session.flush()
    return value


@pytest.mark.asyncio
async def test_note_search_covers_markdown_and_structured_sources(session: AsyncSession) -> None:
    owner = await user(session, "note-search-owner")
    paper = Paper(user_id=owner.id, title="Paper without unique terms", status="ready")
    session.add(paper)
    await session.flush()
    note = Note(user_id=owner.id, paper_id=paper.id, note_type="research",
        title="AtlasNote titleterm", content_markdown="## Method\n**markdownterm** uses $L_{KL}$")
    session.add(note)
    await session.flush()
    profile = ResearchNoteProfile(note_id=note.id, background="backgroundterm",
        research_problem="problemterm", method_summary="methodterm",
        conclusion="conclusionterm", future_work="futureworkterm", my_thoughts="thoughtterm")
    session.add(profile)
    await session.flush()
    session.add(ResearchContribution(research_note_id=profile.id, order_index=0,
        innovation="innovationterm", problem="", prior_limitation="", solution=""))
    session.add(ResearchExperiment(research_note_id=profile.id, order_index=0,
        task="experimentterm", datasets_json=["DatasetUnique"], baselines_json=[],
        metrics_json=[], result="", conclusion=""))
    await session.commit()

    expected = {
        "titleterm": "note_title", "markdownterm": "note_content",
        "problemterm": "research_problem", "innovationterm": "research_contribution",
        "DatasetUnique": "research_experiment", "futureworkterm": "research_conclusion",
        "thoughtterm": "research_thought",
    }
    for query, source in expected.items():
        result = await SearchService(session).search(owner.id, query)
        assert result.total == 1
        assert result.items[0].entity_type == "note"
        assert result.items[0].note.id == note.id
        assert source in {match.source for match in result.items[0].matches}


@pytest.mark.asyncio
async def test_note_search_is_user_scoped_and_aggregates_one_entity(session: AsyncSession) -> None:
    owner = await user(session, "note-aggregate-owner")
    foreign = await user(session, "note-aggregate-foreign")
    for target, title in ((owner, "sharedtoken owner"), (foreign, "sharedtoken foreign")):
        note = Note(user_id=target.id, note_type="general", title=title,
            content_markdown="sharedtoken repeated sharedtoken")
        session.add(note)
    await session.commit()

    result = await SearchService(session).search(owner.id, "sharedtoken")
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].entity_type == "note"
    assert result.items[0].match_count == 2


@pytest.mark.asyncio
async def test_paper_and_note_share_entity_pagination(session: AsyncSession) -> None:
    owner = await user(session, "mixed-page-owner")
    paper = Paper(user_id=owner.id, title="mixedentity term", status="ready")
    session.add(paper)
    await session.flush()
    session.add_all([
        Note(user_id=owner.id, note_type="general", title="mixedentity note one"),
        Note(user_id=owner.id, paper_id=paper.id, note_type="paper", title="mixedentity note two"),
    ])
    await session.commit()

    first = await SearchService(session).search(owner.id, "mixedentity", page=1, page_size=2)
    second = await SearchService(session).search(owner.id, "mixedentity", page=2, page_size=2)
    assert first.total == second.total == 3
    keys = [
        (item.entity_type, item.paper.id if item.entity_type == "paper" else item.note.id)
        for item in [*first.items, *second.items]
    ]
    assert len(keys) == len(set(keys)) == 3
    assert {kind for kind, _ in keys} == {"paper", "note"}
