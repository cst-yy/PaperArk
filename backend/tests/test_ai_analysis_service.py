import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidAIAnalysisError, InvalidNoteError, RevisionConflictError
from app.models import (
    AIAnalysis, AIAnalysisApplication, AIAnalysisSource, Annotation, Chunk, Document,
    Note, NoteEvidence, Paper, ResearchNoteProfile, User,
)
from app.schemas.deep_reading import AIAnalysisApplyRequest, DeepReadingPayload
from app.schemas.rag import RAGSource
from app.schemas.research_note import ResearchProfileAggregate
from app.services.ai_analysis_service import AIAnalysisService
from app.services.research_note_service import ResearchNoteService


def grounded(content: str = "supported") -> dict:
    return {"content": content, "evidence_refs": ["S1"], "insufficient_evidence": False, "grounded": True}


def payload(*, limitation_grounded: bool = False) -> DeepReadingPayload:
    empty = {"content": "", "evidence_refs": [], "insufficient_evidence": True, "grounded": False}
    return DeepReadingPayload.model_validate({
        "background": grounded("AI background"), "prior_work_limitations": grounded("AI prior"),
        "research_problem": grounded("AI problem"), "method_summary": grounded("AI method"),
        "results_summary": grounded("AI result"), "conclusion": grounded("AI conclusion"),
        "limitations": grounded("AI limitation") if limitation_grounded else empty,
        "future_work": empty,
        "contributions": [{"client_id": "c1", "problem": "p", "prior_limitation": "l",
            "innovation": "i", "solution": "s", "evidence_refs": ["S1"],
            "insufficient_evidence": False, "grounded": True}],
        "experiments": [{"client_id": "e1", "task": "classification", "datasets": ["D"],
            "baselines": ["B"], "metrics": ["M"], "result": "R", "conclusion": "C",
            "supports_contribution_client_ids": ["c1"], "evidence_refs": ["S1"],
            "insufficient_evidence": False, "grounded": True}],
    })


async def setup_scope(session: AsyncSession):
    owner = User(id=uuid.uuid4(), username="analysis-owner", email="analysis-owner@test.local", password_hash="")
    other = User(id=uuid.uuid4(), username="analysis-other", email="analysis-other@test.local", password_hash="")
    session.add_all([owner, other]); await session.flush()
    paper = Paper(user_id=owner.id, title="Analysis paper", status="ready")
    other_paper = Paper(user_id=owner.id, title="Other paper", status="ready")
    session.add_all([paper, other_paper]); await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/analysis.pdf", parse_status="ready")
    session.add(document); await session.flush()
    chunk = Chunk(document_id=document.id, chunk_index=0, content="durable source", page_start=2, page_end=2)
    session.add(chunk)
    note = Note(user_id=owner.id, paper_id=paper.id, note_type="research", title="Research", content_markdown="")
    other_note = Note(user_id=owner.id, paper_id=other_paper.id, note_type="research", title="Other", content_markdown="")
    session.add_all([note, other_note]); await session.flush()
    return owner, other, paper, document, chunk, note, other_note


async def save_analysis(session, owner, paper, document, chunk):
    source = RAGSource(
        source_key=f"chunk:{chunk.id}", source_type="paper_chunk", paper_id=paper.id,
        paper_title=paper.title, document_id=document.id, page_start=2, page_end=2,
        title=paper.title, content="durable source", retrieval_method="hybrid",
        retrieval_score=0.9, estimated_tokens=3,
    )
    return await AIAnalysisService(session).save_deep_reading(
        user_id=owner.id, paper_id=paper.id, payload=payload(), sources=[source],
        requested_mode="hybrid", effective_mode="hybrid", provider_name="test-provider", model="test-model",
    )


@pytest.mark.asyncio
async def test_provenance_history_and_source_snapshot_survive_chunk_replacement(session: AsyncSession) -> None:
    owner, other, paper, document, chunk, note, _ = await setup_scope(session)
    draft = await save_analysis(session, owner, paper, document, chunk)
    await session.commit()
    assert draft.analysis_id and draft.source_snapshot_hash and draft.input_hash
    assert len(await AIAnalysisService(session).list_for_paper(owner.id, paper.id)) == 1

    await session.execute(delete(Chunk).where(Chunk.id == chunk.id)); await session.commit()
    detail = await AIAnalysisService(session).get_detail(owner.id, draft.analysis_id)
    assert detail.source_snapshots[0].chunk_id is None
    assert detail.source_snapshots[0].content_snapshot == "durable source"
    assert detail.draft.model == "test-model"
    assert await AIAnalysisService(session).list_for_paper(other.id, paper.id) == []


@pytest.mark.asyncio
async def test_apply_is_server_validated_atomic_and_preserves_user_knowledge(session: AsyncSession) -> None:
    owner, _, paper, document, chunk, note, other_note = await setup_scope(session)
    draft = await save_analysis(session, owner, paper, document, chunk)
    research = ResearchNoteService(session)
    initial = await research.save(owner.id, note.id, ResearchProfileAggregate(
        research_problem="human problem", my_thoughts="never overwrite",
    ))
    await session.commit()
    request = AIAnalysisApplyRequest.model_validate({
        "note_id": str(note.id),
        "apply": {"scalar_fields": ["research_problem", "method_summary"],
            "contribution_client_ids": ["c1"], "experiment_client_ids": ["e1"]},
        "scalar_conflict_policy": "fill_empty", "collections_mode": "append",
        "expected_revision": initial.revision,
    })
    result = await AIAnalysisService(session).apply(owner.id, draft.analysis_id, request)
    await session.commit()
    owner_id, note_id, other_note_id = owner.id, note.id, other_note.id
    applied_revision = result.profile.revision
    assert result.profile.research_problem == "human problem"
    assert result.profile.method_summary == "AI method"
    assert result.profile.my_thoughts == "never overwrite"
    assert len(result.profile.contributions) == len(result.profile.experiments) == 1
    assert result.profile.experiments[0].contribution_ids == [result.profile.contributions[0].id]
    assert await session.scalar(select(func.count()).select_from(AIAnalysisApplication)) == 1
    assert await session.scalar(select(func.count()).select_from(Annotation)) == 0
    assert await session.scalar(select(func.count()).select_from(NoteEvidence)) == 0

    stale = request.model_copy(update={"expected_revision": initial.revision})
    with pytest.raises(RevisionConflictError):
        await AIAnalysisService(session).apply(owner.id, draft.analysis_id, stale)
    await session.rollback()
    assert (await research.get(owner_id, note_id)).revision == applied_revision
    assert await session.scalar(select(func.count()).select_from(AIAnalysisApplication)) == 1

    cross_paper = request.model_copy(update={"note_id": other_note_id, "expected_revision": 0})
    with pytest.raises(InvalidNoteError):
        await AIAnalysisService(session).apply(owner_id, draft.analysis_id, cross_paper)
    await session.rollback()


@pytest.mark.asyncio
async def test_apply_rejects_untrusted_or_incomplete_selections_and_delete_keeps_profile(session: AsyncSession) -> None:
    owner, _, paper, document, chunk, note, _ = await setup_scope(session)
    draft = await save_analysis(session, owner, paper, document, chunk)
    await session.commit()
    owner_id, note_id, analysis_id = owner.id, note.id, draft.analysis_id
    service = AIAnalysisService(session)

    with pytest.raises(ValidationError):
        AIAnalysisApplyRequest.model_validate({"note_id": note_id,
            "apply": {"scalar_fields": ["my_thoughts"]}, "expected_revision": 0})
    invalid = AIAnalysisApplyRequest.model_validate({"note_id": note_id,
        "apply": {"scalar_fields": ["limitations"]}, "expected_revision": 0})
    with pytest.raises(InvalidAIAnalysisError): await service.apply(owner_id, analysis_id, invalid)
    await session.rollback()
    dependent = AIAnalysisApplyRequest.model_validate({"note_id": note_id,
        "apply": {"experiment_client_ids": ["e1"]}, "expected_revision": 0})
    with pytest.raises(InvalidAIAnalysisError): await service.apply(owner_id, analysis_id, dependent)
    await session.rollback()
    assert await session.scalar(select(func.count()).select_from(ResearchNoteProfile)) == 0

    valid = AIAnalysisApplyRequest.model_validate({"note_id": note_id,
        "apply": {"scalar_fields": ["background"]}, "expected_revision": 0})
    await service.apply(owner_id, analysis_id, valid); await session.commit()
    await service.delete(owner_id, analysis_id); await session.commit()
    assert await session.scalar(select(func.count()).select_from(AIAnalysis)) == 0
    assert await session.scalar(select(func.count()).select_from(AIAnalysisSource)) == 0
    assert (await ResearchNoteService(session).get(owner_id, note_id)).background == "AI background"
