import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import event, func, select

from app.models import Document, Keyword, Note, Paper, PaperKeyword, PaperTag, ReadingActivity, Tag, User
from app.schemas.reading_progress import ReadingProgressUpsert
from app.services.backup_service import BackupService
from app.services.dashboard_service import DashboardService
from app.services.reading_progress_service import ReadingProgressService


async def create_user(session, suffix: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.add(User(id=user_id, username=f"dashboard-{suffix}", email=f"dashboard-{suffix}@example.com", password_hash=""))
    await session.flush()
    return user_id


@pytest.mark.asyncio
async def test_dashboard_is_user_scoped_bounded_and_query_count(session, monkeypatch):
    owner_id = await create_user(session, "owner")
    other_id = await create_user(session, "other")
    owner_paper = Paper(user_id=owner_id, title="Owner paper", reading_status="reading")
    finished = Paper(user_id=owner_id, title="Finished paper", reading_status="finished")
    foreign = Paper(user_id=other_id, title="Foreign paper", reading_status="finished")
    session.add_all([owner_paper, finished, foreign])
    await session.flush()
    session.add_all([
        Note(user_id=owner_id, paper_id=owner_paper.id, title="Owner note", note_type="paper"),
        Note(user_id=other_id, paper_id=foreign.id, title="Foreign note", note_type="paper"),
    ])
    tag = Tag(user_id=owner_id, name="RAG", normalized_name="rag")
    keyword = Keyword(user_id=owner_id, display_name="retrieval", normalized_name="retrieval")
    session.add_all([tag, keyword])
    await session.flush()
    session.add_all([
        PaperTag(paper_id=owner_paper.id, tag_id=tag.id),
        PaperKeyword(paper_id=owner_paper.id, keyword_id=keyword.id, source="manual"),
        PaperKeyword(paper_id=owner_paper.id, keyword_id=keyword.id, source="metadata"),
    ])
    await session.flush()
    monkeypatch.setattr(BackupService, "list_backups", lambda self: _empty_backups())

    statements = 0
    def count_query(*_args):
        nonlocal statements
        statements += 1
    event.listen(session.bind.sync_engine, "before_cursor_execute", count_query)
    try:
        result = await DashboardService(session).get_dashboard(owner_id)
    finally:
        event.remove(session.bind.sync_engine, "before_cursor_execute", count_query)

    assert result.overview.model_dump() == {
        "total_papers": 2, "reading_papers": 1,
        "finished_papers": 1, "research_notes": 1,
    }
    assert {item.title for item in result.recent_papers} == {"Finished paper", "Owner paper"}
    assert [item.title for item in result.recent_notes] == ["Owner note"]
    assert result.tags[0].paper_count == 1
    assert result.keywords[0].paper_count == 1
    assert statements <= 10


async def _empty_backups():
    return []


@pytest.mark.asyncio
async def test_progress_upsert_records_one_daily_activity_and_trend_zero_fills(session):
    user_id = await create_user(session, "activity")
    paper = Paper(user_id=user_id, title="Daily reading")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/activity.pdf")
    session.add(document)
    await session.flush()
    service = ReadingProgressService(session)

    await service.upsert_progress(user_id, paper.id, ReadingProgressUpsert(document_id=document.id, current_page=2, total_pages=10, reading_time_seconds_delta=35))
    await service.upsert_progress(user_id, paper.id, ReadingProgressUpsert(document_id=document.id, current_page=3, total_pages=10, reading_time_seconds_delta=25))
    count = await session.scalar(select(func.count(ReadingActivity.id)))
    assert count == 1

    trend = await DashboardService(session).reading_trend(user_id, 7)
    assert len(trend.daily) == 7
    assert trend.daily[-1].date == datetime.now(UTC).date()
    assert trend.daily[-1].papers_read == 1
    assert trend.daily[-1].reading_time_seconds == 60
    assert trend.summary.papers_read == 1
    assert trend.summary.active_days == 1
    assert trend.summary.reading_time_seconds == 60
    assert sum(item.papers_read for item in trend.daily[:-1]) == 0
