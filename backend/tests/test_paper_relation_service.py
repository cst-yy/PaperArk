import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.models import Document, Paper, PaperRelation, Reference, User
from app.services.paper_relation_service import PaperRelationService
from app.services.reference_resolution_service import ReferenceResolutionService


async def user(session: AsyncSession, name: str) -> User:
    value = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(value); await session.flush(); return value


async def paper(session: AsyncSession, owner: User, title: str, **identity) -> Paper:
    value = Paper(user_id=owner.id, title=title, status="ready", **identity)
    session.add(value); await session.flush(); return value


async def document(session: AsyncSession, value: Paper, suffix: str) -> Document:
    result = Document(paper_id=value.id, file_path=f"pdfs/{suffix}.pdf", parse_status="ready")
    session.add(result); await session.flush(); return result


def reference(doc: Document, order: int, *, title=None, doi=None, arxiv_id=None) -> Reference:
    return Reference(
        document_id=doc.id, order_index=order, raw_text=title or doi or arxiv_id or "unmatched",
        title=title, doi=doi, arxiv_id=arxiv_id, page_start=1, page_end=1,
    )


@pytest.mark.asyncio
async def test_resolution_builds_user_scoped_deduplicated_provenanced_citations(session: AsyncSession) -> None:
    owner = await user(session, "relation-owner")
    foreign = await user(session, "relation-foreign")
    source = await paper(session, owner, "Source")
    by_doi = await paper(session, owner, "DOI target", doi="10.1000/doi")
    by_arxiv = await paper(session, owner, "ArXiv target", arxiv_id="2401.12345")
    by_title = await paper(session, owner, "Exact Unicode Title")
    await paper(session, foreign, "Foreign", doi="10.1000/foreign")
    doc = await document(session, source, "source")
    session.add_all([
        reference(doc, 0, doi="10.1000/doi"),
        reference(doc, 1, doi="10.1000/doi"),
        reference(doc, 2, arxiv_id="2401.12345"),
        reference(doc, 3, title="Exact Unicode Title"),
        reference(doc, 4, doi="10.1000/foreign"),
        reference(doc, 5, title="Source"),
        reference(doc, 6, title="Not imported"),
    ])
    await session.flush()

    await ReferenceResolutionService(session).resolve_workspace_for_paper_change(owner.id, by_doi.id)
    await session.commit()
    relations = list((await session.scalars(select(PaperRelation).order_by(PaperRelation.target_paper_id))).all())
    assert {item.target_paper_id for item in relations} == {by_doi.id, by_arxiv.id, by_title.id}
    assert all(item.user_id == owner.id and item.origin == "reference" and item.source_reference_id for item in relations)
    assert all(item.source_paper_id != item.target_paper_id for item in relations)
    assert len([item for item in relations if item.target_paper_id == by_doi.id]) == 1

    response = await PaperRelationService(session).get_relations(owner.id, source.id)
    assert response.outgoing_count == 3 and response.incoming_count == 0
    with pytest.raises(PaperNotFoundError):
        await PaperRelationService(session).get_relations(foreign.id, source.id)


@pytest.mark.asyncio
async def test_replacement_removes_stale_citations_and_deletion_lifecycle_is_safe(session: AsyncSession) -> None:
    owner = await user(session, "replacement-owner")
    source = await paper(session, owner, "Source")
    first = await paper(session, owner, "First", doi="10.1000/first")
    second = await paper(session, owner, "Second", doi="10.1000/second")
    doc = await document(session, source, "replacement")
    session.add_all([reference(doc, 0, doi=first.doi), reference(doc, 1, doi=second.doi)])
    await session.flush()
    resolver = ReferenceResolutionService(session)
    await resolver.resolve_workspace_for_paper_change(owner.id, first.id)
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 2

    await session.execute(delete(Reference).where(Reference.document_id == doc.id))
    session.add(reference(doc, 0, doi=second.doi)); await session.flush()
    await resolver.resolve_workspace_for_paper_change(owner.id, second.id)
    await session.commit()
    assert set((await session.scalars(select(PaperRelation.target_paper_id))).all()) == {second.id}

    relation_id = await session.scalar(select(PaperRelation.id))
    await session.execute(delete(PaperRelation).where(PaperRelation.id == relation_id)); await session.commit()
    assert await session.get(Paper, source.id) is not None and await session.get(Paper, second.id) is not None
    await PaperRelationService(session).sync_citations_for_paper(owner.id, source.id); await session.commit()
    await session.execute(delete(Paper).where(Paper.id == second.id)); await session.commit()
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 0
    assert await session.get(Paper, source.id) is not None


@pytest.mark.asyncio
async def test_late_import_and_identity_update_re_resolve_old_references(session: AsyncSession) -> None:
    owner = await user(session, "late-owner")
    source = await paper(session, owner, "Source")
    doc = await document(session, source, "late")
    old_reference = reference(doc, 0, doi="10.1000/late")
    session.add(old_reference); await session.flush()
    resolver = ReferenceResolutionService(session)
    await resolver.resolve_workspace_for_paper_change(owner.id, source.id)
    assert old_reference.matched_paper_id is None
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 0

    target = await paper(session, owner, "Late target", doi="10.1000/late")
    await resolver.resolve_workspace_for_paper_change(owner.id, target.id)
    assert old_reference.matched_paper_id == target.id
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 1

    target.doi = "10.1000/changed"
    await session.flush()
    await resolver.resolve_workspace_for_paper_change(owner.id, target.id)
    assert old_reference.matched_paper_id is None
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 0
