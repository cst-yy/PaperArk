"""S9-A Note aggregate ownership, CRUD, and paper-scope tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidNoteError, NoteNotFoundError
from app.models import Paper, User
from app.schemas.note import NoteAggregateSave, NoteCreate, NoteUpdate
from app.services.note_service import NoteService


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@notes.test", password_hash="")
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_general_note_crud_and_markdown_aggregate(session: AsyncSession) -> None:
    user = await make_user(session, "note-owner")
    service = NoteService(session)
    note = await service.create_note(user.id, NoteCreate(
        title="Optimization note", content_markdown="Inline $x^2$", note_type="general"
    ))
    saved = await service.save_aggregate(user.id, note.id, NoteAggregateSave(
        paper_id=None, title="Optimization result",
        content_markdown="$$\\mathcal{L}=\\sum_i x_i$$", note_type="general",
    ))
    assert saved.content_markdown.startswith("$$")
    assert (await service.list_notes(user.id))[0].id == note.id
    await service.delete_note(user.id, note.id)
    with pytest.raises(NoteNotFoundError):
        await service.get_note(user.id, note.id)


@pytest.mark.asyncio
async def test_paper_note_requires_owned_paper(session: AsyncSession) -> None:
    owner = await make_user(session, "paper-note-owner")
    other = await make_user(session, "paper-note-other")
    owned_paper = Paper(user_id=owner.id, title="Owned paper", status="ready")
    foreign_paper = Paper(user_id=other.id, title="Foreign paper", status="ready")
    session.add_all([owned_paper, foreign_paper])
    await session.flush()
    service = NoteService(session)

    note = await service.create_note(owner.id, NoteCreate(
        paper_id=owned_paper.id, title="Paper note", note_type="paper"
    ))
    assert note.paper_id == owned_paper.id
    assert [item.id for item in await service.list_notes(owner.id, owned_paper.id)] == [note.id]
    with pytest.raises(InvalidNoteError):
        await service.create_note(owner.id, NoteCreate(
            paper_id=foreign_paper.id, title="Invalid", note_type="paper"
        ))
    with pytest.raises(InvalidNoteError):
        await service.update_note(owner.id, note.id, NoteUpdate(paper_id=foreign_paper.id))


@pytest.mark.asyncio
async def test_note_detail_update_and_delete_are_user_scoped(session: AsyncSession) -> None:
    owner = await make_user(session, "scope-owner")
    other = await make_user(session, "scope-other")
    note = await NoteService(session).create_note(owner.id, NoteCreate(title="Private"))
    foreign_service = NoteService(session)
    for operation in (
        lambda: foreign_service.get_note(other.id, note.id),
        lambda: foreign_service.update_note(other.id, note.id, NoteUpdate(title="Stolen")),
        lambda: foreign_service.delete_note(other.id, note.id),
    ):
        with pytest.raises(NoteNotFoundError):
            await operation()
    assert (await NoteService(session).get_note(owner.id, note.id)).title == "Private"
