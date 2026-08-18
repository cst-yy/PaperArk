import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicatePaperRelationError, InvalidPaperRelationError
from app.models import Annotation, Document, Paper, PaperRelation, PaperRelationEvidence, Reference, User
from app.schemas.knowledge_relation import (
    ManualRelationCreate, ManualRelationUpdate, RelationEvidenceInput, RelationEvidenceReplacement,
)
from app.services.knowledge_relation_service import KnowledgeRelationService


async def make_user(db, name):
    item = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    db.add(item); await db.flush(); return item


async def make_paper(db, user, title):
    item = Paper(user_id=user.id, title=title, status="ready")
    db.add(item); await db.flush(); return item


@pytest.mark.asyncio
async def test_manual_crud_direction_and_similar_canonical_uniqueness(session: AsyncSession):
    owner, foreign = await make_user(session, "kr-owner"), await make_user(session, "kr-foreign")
    a, b = await make_paper(session, owner, "A"), await make_paper(session, owner, "B")
    outsider = await make_paper(session, foreign, "X")
    service = KnowledgeRelationService(session)
    forward = await service.create(owner.id, a.id, ManualRelationCreate(target_paper_id=b.id, relation_type="extends", note="why"))
    reverse = await service.create(owner.id, b.id, ManualRelationCreate(target_paper_id=a.id, relation_type="extends"))
    assert forward.id != reverse.id and forward.note == "why"
    await service.update(owner.id, a.id, forward.id, ManualRelationUpdate(
        target_paper_id=b.id, relation_type="improves", note="better"))
    assert (await service.get(owner.id, forward.id)).relation_type == "improves"
    with pytest.raises(InvalidPaperRelationError):
        await service.create(owner.id, a.id, ManualRelationCreate(target_paper_id=a.id, relation_type="uses"))
    with pytest.raises(InvalidPaperRelationError):
        await service.create(owner.id, a.id, ManualRelationCreate(target_paper_id=outsider.id, relation_type="uses"))
    similar = await service.create(owner.id, b.id, ManualRelationCreate(target_paper_id=a.id, relation_type="similar"))
    assert (similar.source_paper_id, similar.target_paper_id) == tuple(sorted((a.id, b.id), key=str))
    with pytest.raises(DuplicatePaperRelationError):
        await service.create(owner.id, a.id, ManualRelationCreate(target_paper_id=b.id, relation_type="similar"))
    await service.delete(owner.id, a.id, forward.id)
    assert await session.get(PaperRelation, forward.id) is None


@pytest.mark.asyncio
async def test_reference_edges_are_immutable_and_evidence_replacement_is_atomic(session: AsyncSession):
    owner, foreign = await make_user(session, "e-owner"), await make_user(session, "e-foreign")
    a, b = await make_paper(session, owner, "A"), await make_paper(session, owner, "B")
    x = await make_paper(session, foreign, "X")
    da, dx = Document(paper_id=a.id, file_path="a.pdf"), Document(paper_id=x.id, file_path="x.pdf")
    session.add_all([da, dx]); await session.flush()
    annotation = Annotation(user_id=owner.id, paper_id=a.id, document_id=da.id, type="highlight",
        page_number=1, selected_text="Compared with baseline")
    foreign_annotation = Annotation(user_id=foreign.id, paper_id=x.id, document_id=dx.id, type="highlight",
        page_number=1, selected_text="foreign")
    reference = Reference(document_id=da.id, order_index=0, raw_text="Baseline reference", page_start=1, page_end=1)
    session.add_all([annotation, foreign_annotation, reference]); await session.flush()
    citation = PaperRelation(user_id=owner.id, source_paper_id=a.id, target_paper_id=b.id,
        relation_type="cites", origin="reference", source_reference_id=reference.id)
    session.add(citation); await session.flush()
    service = KnowledgeRelationService(session)
    with pytest.raises(InvalidPaperRelationError): await service.delete(owner.id, a.id, citation.id)
    relation = await service.create(owner.id, a.id, ManualRelationCreate(target_paper_id=b.id, relation_type="supports"))
    replaced = await service.replace_evidence(owner.id, relation.id, RelationEvidenceReplacement(evidence=[
        RelationEvidenceInput(annotation_id=annotation.id), RelationEvidenceInput(source_reference_id=reference.id)]))
    assert [item.quote_snapshot for item in replaced.evidence] == ["Compared with baseline", "Baseline reference"]
    with pytest.raises(InvalidPaperRelationError):
        await service.replace_evidence(owner.id, relation.id, RelationEvidenceReplacement(
            evidence=[RelationEvidenceInput(annotation_id=foreign_annotation.id)]))
    assert await session.scalar(select(func.count()).select_from(PaperRelationEvidence).where(
        PaperRelationEvidence.relation_id == relation.id)) == 2
    await session.execute(PaperRelationEvidence.__table__.delete().where(PaperRelationEvidence.relation_id == relation.id))
    assert await session.get(Annotation, annotation.id) is not None and await session.get(Reference, reference.id) is not None
