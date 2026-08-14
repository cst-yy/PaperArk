import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, update

from app.core.exceptions import DocumentNotFoundError, PaperNotFoundError
from app.models import Document, Paper, ReadingProgress, User
from pydantic import ValidationError

from app.schemas.reading_progress import ReadingProgressUpsert
from app.services.paper_service import PaperService
from app.services.reading_progress_service import ReadingProgressService


async def create_user(session, suffix: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    session.add(User(
        id=user_id,
        username=f"reading-{suffix}",
        email=f"reading-{suffix}@example.com",
        password_hash="",
    ))
    await session.flush()
    return user_id


async def create_paper_with_document(session, user_id: uuid.UUID, title: str):
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title=title)
    document = Document(
        id=uuid.uuid4(),
        paper_id=paper.id,
        file_path=f"pdfs/{uuid.uuid4()}.pdf",
    )
    session.add_all([paper, document])
    await session.flush()
    return paper, document


@pytest.mark.asyncio
async def test_reading_progress_creates_updates_and_returns_document_scope(session):
    user_id = await create_user(session, "owner")
    paper, document = await create_paper_with_document(session, user_id, "Progress paper")
    assert paper.reading_status == "unread"
    service = ReadingProgressService(session)

    created = await service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=3, total_pages=12),
    )
    assert created.document_id == document.id
    assert created.current_page == 3
    assert created.total_pages == 12
    assert created.progress_ratio == pytest.approx(0.25)
    await session.refresh(paper)
    assert paper.reading_status == "reading"

    updated = await service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=8, total_pages=12),
    )
    assert updated.current_page == 8
    assert updated.progress_ratio == pytest.approx(8 / 12)
    assert await session.scalar(select(func.count()).select_from(ReadingProgress)) == 1

    fetched = await service.get_progress(user_id, paper.id, document.id)
    assert fetched is not None
    assert fetched.current_page == 8
    assert fetched.document_id == document.id


@pytest.mark.asyncio
async def test_reading_status_is_user_scoped_and_allows_manual_transitions(session):
    owner_id = await create_user(session, "status-owner")
    other_id = await create_user(session, "status-other")
    paper, _ = await create_paper_with_document(session, owner_id, "Manual status")
    service = PaperService(session)

    await service.set_reading_status(owner_id, paper.id, "finished")
    await session.refresh(paper)
    assert paper.reading_status == "finished"

    await service.set_reading_status(owner_id, paper.id, "reading")
    await session.refresh(paper)
    assert paper.reading_status == "reading"

    with pytest.raises(PaperNotFoundError):
        await service.set_reading_status(other_id, paper.id, "archived")


@pytest.mark.asyncio
async def test_progress_does_not_override_finished_or_archived_reading_status(session):
    user_id = await create_user(session, "status-preserve")
    paper, document = await create_paper_with_document(session, user_id, "Status preserve")
    progress_service = ReadingProgressService(session)
    paper_service = PaperService(session)

    await paper_service.set_reading_status(user_id, paper.id, "finished")
    await progress_service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=2, total_pages=8),
    )
    await session.refresh(paper)
    assert paper.reading_status == "finished"

    await paper_service.set_reading_status(user_id, paper.id, "archived")
    await progress_service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=3, total_pages=8),
    )
    await session.refresh(paper)
    assert paper.reading_status == "archived"


@pytest.mark.asyncio
async def test_reading_progress_rejects_foreign_paper_and_mismatched_document(session):
    owner_id = await create_user(session, "owner-boundary")
    other_id = await create_user(session, "other-boundary")
    owner_paper, owner_document = await create_paper_with_document(session, owner_id, "Owner paper")
    other_paper, other_document = await create_paper_with_document(session, other_id, "Other paper")
    service = ReadingProgressService(session)

    with pytest.raises(PaperNotFoundError):
        await service.get_progress(other_id, owner_paper.id, owner_document.id)

    with pytest.raises(DocumentNotFoundError):
        await service.upsert_progress(
            owner_id,
            owner_paper.id,
            ReadingProgressUpsert(document_id=other_document.id, current_page=1, total_pages=4),
        )

    with pytest.raises(DocumentNotFoundError):
        await service.get_progress(owner_id, owner_paper.id, other_document.id)


def test_reading_progress_rejects_invalid_page_ranges():
    with pytest.raises(ValidationError):
        ReadingProgressUpsert(document_id=uuid.uuid4(), current_page=0, total_pages=3)
    with pytest.raises(ValidationError):
        ReadingProgressUpsert(document_id=uuid.uuid4(), current_page=4, total_pages=3)
    with pytest.raises(ValidationError):
        ReadingProgressUpsert(document_id=uuid.uuid4(), current_page=1, total_pages=0)


@pytest.mark.asyncio
async def test_reading_progress_is_deleted_when_document_is_deleted(session):
    user_id = await create_user(session, "cascade")
    paper, document = await create_paper_with_document(session, user_id, "Cascade paper")
    service = ReadingProgressService(session)
    await service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=2, total_pages=5),
    )
    await session.flush()

    await session.delete(document)
    await session.flush()

    assert await session.scalar(select(func.count()).select_from(ReadingProgress)) == 0


@pytest.mark.asyncio
async def test_recent_reading_is_user_scoped_ordered_and_document_scoped(session):
    owner_id = await create_user(session, "recent-owner")
    other_id = await create_user(session, "recent-other")
    paper_a, document_a = await create_paper_with_document(session, owner_id, "Older reading")
    paper_b, document_b = await create_paper_with_document(session, owner_id, "Newer reading")
    document_b_second = Document(
        id=uuid.uuid4(),
        paper_id=paper_b.id,
        file_path=f"pdfs/{uuid.uuid4()}.pdf",
    )
    session.add(document_b_second)
    other_paper, other_document = await create_paper_with_document(session, other_id, "Foreign reading")
    service = ReadingProgressService(session)

    for paper, document, page in [
        (paper_a, document_a, 2),
        (paper_b, document_b, 3),
        (paper_b, document_b_second, 4),
        (other_paper, other_document, 5),
    ]:
        await service.upsert_progress(
            owner_id if paper.user_id == owner_id else other_id,
            paper.id,
            ReadingProgressUpsert(document_id=document.id, current_page=page, total_pages=10),
        )

    now = datetime.now(timezone.utc)
    timestamps = {
        document_a.id: now - timedelta(hours=2),
        document_b.id: now - timedelta(hours=1),
        document_b_second.id: now,
        other_document.id: now + timedelta(hours=1),
    }
    for document_id, timestamp in timestamps.items():
        await session.execute(
            update(ReadingProgress)
            .where(ReadingProgress.document_id == document_id)
            .values(last_read_at=timestamp)
        )
    await session.flush()

    items = await service.list_recent_reading(owner_id, limit=2)

    assert [item.document.id for item in items] == [document_b_second.id, document_b.id]
    assert [item.paper.id for item in items] == [paper_b.id, paper_b.id]
    assert [item.current_page for item in items] == [4, 3]
    assert all(item.paper.id != other_paper.id for item in items)


@pytest.mark.asyncio
async def test_get_progress_does_not_change_last_read_at(session):
    user_id = await create_user(session, "recent-get")
    paper, document = await create_paper_with_document(session, user_id, "Read timestamp")
    service = ReadingProgressService(session)
    await service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=2, total_pages=8),
    )
    saved_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    await session.execute(
        update(ReadingProgress)
        .where(ReadingProgress.document_id == document.id)
        .values(last_read_at=saved_at)
    )
    await session.flush()

    progress = await service.get_progress(user_id, paper.id, document.id)

    assert progress is not None
    assert progress.last_read_at == saved_at


@pytest.mark.asyncio
async def test_reading_progress_is_deleted_when_paper_is_deleted(session):
    user_id = await create_user(session, "paper-cascade")
    paper, document = await create_paper_with_document(session, user_id, "Paper cascade")
    service = ReadingProgressService(session)
    await service.upsert_progress(
        user_id,
        paper.id,
        ReadingProgressUpsert(document_id=document.id, current_page=2, total_pages=5),
    )
    await session.flush()

    await session.delete(paper)
    await session.flush()

    assert await session.scalar(select(func.count()).select_from(ReadingProgress)) == 0
