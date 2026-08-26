import uuid

import pytest

from app.core.exceptions import PaperNotFoundError, RevisionConflictError
from app.models import Paper, User
from app.schemas.paper import PaperUpdate
from app.schemas.paper_list import BatchPaperUpdate, PaperListPreference, PaperListViewSettingsPatch
from app.services.paper_list_service import PaperListService
from app.services.paper_service import PaperService


async def _user(session, name: str) -> uuid.UUID:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@example.com", password_hash="")
    session.add(user)
    await session.flush()
    return user.id


@pytest.mark.asyncio
async def test_metadata_revision_rejects_stale_update(session):
    user_id = await _user(session, "revision-owner")
    paper = Paper(user_id=user_id, title="Initial")
    session.add(paper)
    await session.flush()
    service = PaperService(session)

    updated = await service.update_paper(
        user_id, paper.id, PaperUpdate(title="Client A", expected_revision=1)
    )
    assert updated.title == "Client A"
    assert updated.metadata_revision == 2

    with pytest.raises(RevisionConflictError):
        await service.update_paper(
            user_id, paper.id, PaperUpdate(title="Client B", expected_revision=1)
        )
    assert (await service.get_paper(user_id, paper.id)).title == "Client A"


@pytest.mark.asyncio
async def test_batch_update_validates_all_ownership_before_writing(session):
    owner = await _user(session, "batch-owner")
    foreign = await _user(session, "batch-foreign")
    owned = Paper(user_id=owner, title="Owned", reading_status="unread")
    inaccessible = Paper(user_id=foreign, title="Foreign", reading_status="unread")
    session.add_all([owned, inaccessible])
    await session.flush()

    with pytest.raises(PaperNotFoundError):
        await PaperListService(session).batch_update(
            owner,
            BatchPaperUpdate(
                paper_ids=[owned.id, inaccessible.id], reading_status="finished"
            ),
        )
    await session.refresh(owned)
    assert owned.reading_status == "unread"
    assert owned.metadata_revision == 1


@pytest.mark.asyncio
async def test_paper_list_preference_round_trip_and_is_user_scoped(session):
    owner = await _user(session, "preference-owner")
    other = await _user(session, "preference-other")
    service = PaperListService(session)
    preference = PaperListPreference(visible_columns=["title", "authors"], column_order=["authors", "title"])
    await service.save_preference(owner, preference)

    assert (await service.get_preference(owner)).column_order == ["authors", "title"]
    assert (await service.get_preference(other)).visible_columns == []


@pytest.mark.asyncio
async def test_view_settings_patch_is_partitioned_revisioned_and_user_scoped(session):
    owner = await _user(session, "view-owner")
    other = await _user(session, "view-other")
    service = PaperListService(session)
    first = await service.patch_view_settings(owner, PaperListViewSettingsPatch(
        expected_revision=0,
        columns={"visible": ["title", "authors"], "order": ["authors", "title"],
                 "widths": {"title": {"preferred_width": 360, "mode": "manual"}}},
    ))
    assert first.revision == 1
    assert first.columns.widths["title"].preferred_width == 360
    second = await service.patch_view_settings(owner, PaperListViewSettingsPatch(
        expected_revision=1, query={"q": "federated", "page_size": 100}
    ))
    assert second.revision == 2 and second.query.q == "federated"
    assert second.columns.widths["title"].preferred_width == 360
    assert (await service.get_view_settings(other)).revision == 0

    with pytest.raises(RevisionConflictError):
        await service.patch_view_settings(owner, PaperListViewSettingsPatch(
            expected_revision=1, layout={"scroll_top": 120}
        ))
