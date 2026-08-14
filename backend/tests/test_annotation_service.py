import uuid

import pytest

from app.core.exceptions import AnnotationNotFoundError, InvalidAnnotationError
from app.models import Document, Paper, User
from app.services.annotation_service import AnnotationService


def text_position():
    return {"kind": "text", "rects": [{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}]}


@pytest.mark.asyncio
async def test_annotation_service_enforces_document_and_user_scope(session):
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    owner_paper = Paper(id=uuid.uuid4(), user_id=owner_id, title="Owner paper")
    other_paper = Paper(id=uuid.uuid4(), user_id=other_id, title="Other paper")
    owner_doc = Document(id=uuid.uuid4(), paper_id=owner_paper.id, file_path="pdfs/owner.pdf")
    other_doc = Document(id=uuid.uuid4(), paper_id=other_paper.id, file_path="pdfs/other.pdf")
    session.add_all([
        User(id=owner_id, username="owner", email="owner@example.com", password_hash=""),
        User(id=other_id, username="other", email="other@example.com", password_hash=""),
    ])
    await session.flush()
    session.add_all([owner_paper, other_paper, owner_doc, other_doc])
    await session.flush()

    service = AnnotationService(session)
    annotation = await service.create(
        owner_id,
        paper_id=owner_paper.id,
        document_id=owner_doc.id,
        type="highlight",
        page_number=2,
        selected_text="Important contribution",
        position_data=text_position(),
        color="yellow",
    )
    assert annotation.document_id == owner_doc.id
    assert annotation.position_data["kind"] == "text"

    with pytest.raises(AnnotationNotFoundError):
        await service.update(other_id, annotation.id, comment="attempted access")

    with pytest.raises(InvalidAnnotationError):
        await service.create(
            owner_id,
            paper_id=owner_paper.id,
            document_id=other_doc.id,
            type="highlight",
            page_number=1,
            selected_text="Invalid reference",
            position_data=text_position(),
            color="yellow",
        )


@pytest.mark.asyncio
async def test_annotation_service_rejects_out_of_bounds_normalized_rect(session):
    user_id = uuid.uuid4()
    paper = Paper(id=uuid.uuid4(), user_id=user_id, title="Paper")
    document = Document(id=uuid.uuid4(), paper_id=paper.id, file_path="pdfs/paper.pdf")
    session.add(User(id=user_id, username="researcher", email="researcher@example.com", password_hash=""))
    await session.flush()
    session.add_all([paper, document])
    await session.flush()

    with pytest.raises(InvalidAnnotationError):
        await AnnotationService(session).create(
            user_id,
            paper_id=paper.id,
            document_id=document.id,
            type="area",
            page_number=1,
            position_data={"kind": "area", "rect": {"x": 0.8, "y": 0.1, "width": 0.3, "height": 0.2}},
            color="yellow",
        )
