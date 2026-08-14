"""S9-B Evidence Linking ownership, ordering, rollback, and cascade tests."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidNoteError
from app.models import Annotation, Document, Note, NoteEvidence, Paper, User
from app.schemas.note import NoteCreate
from app.services.note_service import NoteService


async def make_user(session: AsyncSession, name: str) -> User:
    user = User(id=uuid.uuid4(), username=name, email=f"{name}@evidence.test", password_hash="")
    session.add(user)
    await session.flush()
    return user


async def make_paper_annotation(session: AsyncSession, user: User, title: str, text: str) -> tuple[Paper, Annotation]:
    paper = Paper(user_id=user.id, title=title, status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path=f"pdfs/{paper.id}.pdf", parse_status="ready")
    session.add(document)
    await session.flush()
    annotation = Annotation(user_id=user.id, paper_id=paper.id, document_id=document.id,
        type="highlight", page_number=2, selected_text=text,
        position_data={"kind": "text", "rects": [{"x": .1, "y": .1, "width": .2, "height": .05}]})
    session.add(annotation)
    await session.flush()
    return paper, annotation


@pytest.mark.asyncio
async def test_replace_reorders_evidence_and_preserves_snapshot(session: AsyncSession) -> None:
    user = await make_user(session, "replace-owner")
    paper, first = await make_paper_annotation(session, user, "Paper A", "first quote")
    document = await session.scalar(select(Document).where(Document.paper_id == paper.id))
    second = Annotation(user_id=user.id, paper_id=paper.id, document_id=document.id,
        type="comment", page_number=4, comment="second comment")
    session.add(second)
    await session.flush()
    service = NoteService(session)
    note = await service.create_note(user.id, NoteCreate(
        paper_id=paper.id, title="Evidence note", note_type="paper", annotation_ids=[first.id, second.id]
    ))
    assert [item.annotation_id for item in note.evidence] == [first.id, second.id]
    assert [item.order_index for item in note.evidence] == [0, 1]
    assert note.evidence[0].quote_snapshot == "first quote"

    first.selected_text = "edited annotation"
    reordered = await service.replace_evidence(user.id, note.id, [second.id, first.id])
    assert [item.annotation_id for item in reordered.evidence] == [second.id, first.id]
    assert reordered.evidence[1].quote_snapshot == "first quote"


@pytest.mark.asyncio
async def test_replacement_failure_keeps_original_collection(session: AsyncSession) -> None:
    owner = await make_user(session, "rollback-owner")
    foreign = await make_user(session, "rollback-foreign")
    paper, valid = await make_paper_annotation(session, owner, "Owned", "valid")
    _, foreign_annotation = await make_paper_annotation(session, foreign, "Foreign", "foreign")
    service = NoteService(session)
    note = await service.create_note(owner.id, NoteCreate(
        paper_id=paper.id, title="Rollback", note_type="paper", annotation_ids=[valid.id]
    ))
    owner_id, note_id, valid_id, foreign_id = owner.id, note.id, valid.id, foreign_annotation.id
    await session.commit()
    with pytest.raises(InvalidNoteError):
        await service.replace_evidence(owner_id, note_id, [valid_id, foreign_id])
    await session.rollback()
    persisted = await NoteService(session).get_note(owner_id, note_id)
    assert [item.annotation_id for item in persisted.evidence] == [valid_id]


@pytest.mark.asyncio
async def test_paper_scope_general_note_and_duplicate_rules(session: AsyncSession) -> None:
    user = await make_user(session, "scope-owner")
    paper_a, annotation_a = await make_paper_annotation(session, user, "A", "A quote")
    _, annotation_b = await make_paper_annotation(session, user, "B", "B quote")
    service = NoteService(session)
    paper_note = await service.create_note(user.id, NoteCreate(paper_id=paper_a.id, title="A note", note_type="paper"))
    with pytest.raises(InvalidNoteError):
        await service.replace_evidence(user.id, paper_note.id, [annotation_b.id])
    with pytest.raises(InvalidNoteError):
        await service.replace_evidence(user.id, paper_note.id, [annotation_a.id, annotation_a.id])
    general = await service.create_note(user.id, NoteCreate(
        title="Cross-paper", note_type="general", annotation_ids=[annotation_a.id, annotation_b.id]
    ))
    assert len(general.evidence) == 2


@pytest.mark.asyncio
async def test_note_and_annotation_deletes_only_cascade_links(session: AsyncSession) -> None:
    user = await make_user(session, "cascade-owner")
    paper, annotation = await make_paper_annotation(session, user, "Cascade", "durable quote")
    service = NoteService(session)
    note = await service.create_note(user.id, NoteCreate(
        paper_id=paper.id, title="Delete note", note_type="paper", annotation_ids=[annotation.id]
    ))
    await service.delete_note(user.id, note.id)
    assert await session.get(Annotation, annotation.id) is not None
    assert await session.scalar(select(func.count()).select_from(NoteEvidence)) == 0

    note = await service.create_note(user.id, NoteCreate(
        paper_id=paper.id, title="Keep note", note_type="paper", annotation_ids=[annotation.id]
    ))
    await session.delete(annotation)
    await session.flush()
    assert await session.get(Note, note.id) is not None
    assert await session.scalar(select(func.count()).select_from(NoteEvidence)) == 0
