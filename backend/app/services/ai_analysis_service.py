from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AIAnalysisNotFoundError, InvalidAIAnalysisError, InvalidNoteError
from app.models import AIAnalysis, AIAnalysisApplication, AIAnalysisSource
from app.schemas.ai import AICitation
from app.schemas.deep_reading import (
    AIAnalysisApplyRequest, AIAnalysisApplyResponse, AIAnalysisBrief,
    AIAnalysisDetail, AIAnalysisSourceResponse, DeepReadingDraft,
    DeepReadingPayload,
)
from app.schemas.research_note import ContributionInput, ExperimentInput, ResearchProfileAggregate
from app.schemas.rag import RAGSource
from app.services.deep_reading_prompt import DEEP_READING_PROMPT_VERSION
from app.services.research_note_service import ResearchNoteService


class AIAnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_deep_reading(
        self, *, user_id: uuid.UUID, paper_id: uuid.UUID, payload: DeepReadingPayload,
        sources: list[RAGSource], requested_mode: str, effective_mode: str,
        provider_name: str, model: str,
    ) -> DeepReadingDraft:
        source_hash = self.source_snapshot_hash(sources)
        input_hash = self.input_hash(
            paper_id=paper_id, provider_name=provider_name, model=model,
            retrieval_mode=requested_mode, source_snapshot_hash=source_hash,
        )
        analysis = AIAnalysis(
            user_id=user_id, paper_id=paper_id, analysis_type="deep_reading", status="ready",
            provider_name=provider_name, model=model, prompt_version=DEEP_READING_PROMPT_VERSION,
            retrieval_mode=requested_mode, source_snapshot_hash=source_hash,
            input_hash=input_hash, result_json=payload.model_dump(mode="json"),
        )
        self.db.add(analysis)
        await self.db.flush()
        for index, source in enumerate(sources):
            self.db.add(AIAnalysisSource(
                analysis_id=analysis.id, order_index=index, source_key=source.source_key,
                source_type=source.source_type, paper_id=paper_id, document_id=source.document_id,
                chunk_id=self._chunk_id(source.source_key), section_title=source.section_title,
                page_start=source.page_start, page_end=source.page_end,
                title=source.paper_title or source.title,
                content_snapshot=source.content, content_hash=self._content_hash(source.content),
                retrieval_score=source.retrieval_score,
            ))
        await self.db.flush()
        return DeepReadingDraft(
            **payload.model_dump(), paper_id=paper_id, requested_mode=requested_mode,
            effective_mode=effective_mode, sources=self._citations_from_rag(sources),
            source_count=len(sources), analysis_id=analysis.id, provider_name=provider_name,
            model=model, prompt_version=analysis.prompt_version,
            source_snapshot_hash=source_hash, input_hash=input_hash, created_at=analysis.created_at,
        )

    async def get_detail(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> AIAnalysisDetail:
        analysis = await self._analysis(user_id, analysis_id)
        payload = self._payload(analysis)
        citations = [self._citation_from_snapshot(source) for source in analysis.sources]
        draft = DeepReadingDraft(
            **payload.model_dump(), paper_id=analysis.paper_id,
            requested_mode=analysis.retrieval_mode, effective_mode=analysis.retrieval_mode,
            sources=citations, source_count=len(citations), analysis_id=analysis.id,
            provider_name=analysis.provider_name, model=analysis.model,
            prompt_version=analysis.prompt_version,
            source_snapshot_hash=analysis.source_snapshot_hash, input_hash=analysis.input_hash,
            created_at=analysis.created_at,
        )
        snapshots = [AIAnalysisSourceResponse(
            label=f"S{source.order_index + 1}", source_key=source.source_key,
            source_type=source.source_type, paper_id=source.paper_id,
            document_id=source.document_id, chunk_id=source.chunk_id,
            section_title=source.section_title, page_start=source.page_start,
            page_end=source.page_end, title=source.title,
            content_snapshot=source.content_snapshot, content_hash=source.content_hash,
            retrieval_score=source.retrieval_score,
        ) for source in analysis.sources]
        return AIAnalysisDetail(draft=draft, source_snapshots=snapshots)

    async def list_for_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> list[AIAnalysisBrief]:
        analyses = (await self.db.scalars(
            select(AIAnalysis).where(
                AIAnalysis.user_id == user_id, AIAnalysis.paper_id == paper_id,
                AIAnalysis.analysis_type == "deep_reading",
            ).options(selectinload(AIAnalysis.sources), selectinload(AIAnalysis.applications))
            .order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc())
        )).all()
        return [AIAnalysisBrief(
            analysis_id=item.id, analysis_type="deep_reading", status="ready",
            provider_name=item.provider_name, model=item.model,
            prompt_version=item.prompt_version, retrieval_mode=item.retrieval_mode,
            source_count=len(item.sources), application_count=len(item.applications),
            source_snapshot_hash=item.source_snapshot_hash, created_at=item.created_at,
        ) for item in analyses]

    async def delete(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> None:
        result = await self.db.execute(delete(AIAnalysis).where(
            AIAnalysis.id == analysis_id, AIAnalysis.user_id == user_id
        ))
        if result.rowcount != 1:
            raise AIAnalysisNotFoundError("AI analysis not found")

    async def apply(
        self, user_id: uuid.UUID, analysis_id: uuid.UUID, request: AIAnalysisApplyRequest
    ) -> AIAnalysisApplyResponse:
        analysis = await self._analysis(user_id, analysis_id)
        payload = self._payload(analysis)
        research = ResearchNoteService(self.db)
        note = await research._note(user_id, request.note_id)
        if note.paper_id != analysis.paper_id:
            raise InvalidNoteError("AI analysis can only be applied to a research note for the same paper")
        if not (request.apply.scalar_fields or request.apply.contribution_client_ids or request.apply.experiment_client_ids):
            raise InvalidAIAnalysisError("Select at least one grounded field or item to apply")

        contributions = {item.client_id: item for item in payload.contributions}
        experiments = {item.client_id: item for item in payload.experiments}
        selected_contributions = self._selected(contributions, request.apply.contribution_client_ids, "contribution")
        selected_experiments = self._selected(experiments, request.apply.experiment_client_ids, "experiment")
        for field_name in request.apply.scalar_fields:
            self._require_grounded(getattr(payload, field_name), field_name)
        for item in [*selected_contributions, *selected_experiments]:
            self._require_grounded(item, item.client_id)
        selected_contribution_ids = {item.client_id for item in selected_contributions}
        for experiment in selected_experiments:
            missing = set(experiment.supports_contribution_client_ids) - selected_contribution_ids
            if missing:
                raise InvalidAIAnalysisError(
                    f"Experiment {experiment.client_id} requires selected contributions: {', '.join(sorted(missing))}"
                )

        current_response = await research.get(user_id, request.note_id)
        current = self._aggregate_from_response(current_response)
        for field_name in request.apply.scalar_fields:
            if request.scalar_conflict_policy == "replace" or not getattr(current, field_name):
                setattr(current, field_name, getattr(payload, field_name).content)

        # AI client IDs are untrusted model output and may already consume the
        # aggregate's 100-character limit.  Use compact server-owned IDs so an
        # otherwise valid stored result cannot fail during apply.
        contribution_id_map = {
            item.client_id: f"ai-c-{index}-{analysis.id.hex[:12]}"
            for index, item in enumerate(selected_contributions)
        }
        ai_contributions = [ContributionInput(
            client_id=contribution_id_map[item.client_id], problem=item.problem,
            prior_limitation=item.prior_limitation, innovation=item.innovation,
            solution=item.solution, evidence_ids=[],
        ) for item in selected_contributions]
        ai_experiments = [ExperimentInput(
            client_id=f"ai-e-{index}-{analysis.id.hex[:12]}", task=item.task,
            datasets=item.datasets, baselines=item.baselines, metrics=item.metrics,
            result=item.result, conclusion=item.conclusion,
            supports_contribution_client_ids=[contribution_id_map[value] for value in item.supports_contribution_client_ids],
            evidence_ids=[],
        ) for index, item in enumerate(selected_experiments)]
        if request.collections_mode == "replace":
            current.contributions, current.experiments = ai_contributions, ai_experiments
        else:
            current.contributions.extend(ai_contributions)
            current.experiments.extend(ai_experiments)

        profile = await research.save(
            user_id, request.note_id, current, expected_revision=request.expected_revision
        )
        application = AIAnalysisApplication(
            analysis_id=analysis.id, note_id=request.note_id,
            application_mode=f"{request.scalar_conflict_policy}:{request.collections_mode}",
            applied_fields_json=request.apply.model_dump(mode="json"),
            profile_revision=profile.revision,
        )
        self.db.add(application)
        await self.db.flush()
        return AIAnalysisApplyResponse(
            application_id=application.id, analysis_id=analysis.id, profile=profile
        )

    async def _analysis(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> AIAnalysis:
        analysis = await self.db.scalar(select(AIAnalysis).where(
            AIAnalysis.id == analysis_id, AIAnalysis.user_id == user_id
        ).options(selectinload(AIAnalysis.sources), selectinload(AIAnalysis.applications)))
        if analysis is None:
            raise AIAnalysisNotFoundError("AI analysis not found")
        return analysis

    @staticmethod
    def _payload(analysis: AIAnalysis) -> DeepReadingPayload:
        try:
            return DeepReadingPayload.model_validate(analysis.result_json)
        except Exception as exc:
            raise InvalidAIAnalysisError("Stored AI analysis has an invalid result contract") from exc

    @staticmethod
    def _selected(items: dict, selected_ids: list[str], label: str) -> list:
        missing = set(selected_ids) - set(items)
        if missing:
            raise InvalidAIAnalysisError(f"Unknown {label} client_id: {', '.join(sorted(missing))}")
        return [items[value] for value in selected_ids]

    @staticmethod
    def _require_grounded(item, label: str) -> None:
        if not item.grounded or item.insufficient_evidence:
            raise InvalidAIAnalysisError(f"{label} is not grounded and cannot be applied")

    @staticmethod
    def _aggregate_from_response(response) -> ResearchProfileAggregate:
        if response is None:
            return ResearchProfileAggregate()
        contribution_map = {item.id: f"existing:{item.id}" for item in response.contributions}
        return ResearchProfileAggregate(
            background=response.background, prior_work_limitations=response.prior_work_limitations,
            research_problem=response.research_problem, method_summary=response.method_summary,
            results_summary=response.results_summary, conclusion=response.conclusion,
            limitations=response.limitations, future_work=response.future_work,
            my_thoughts=response.my_thoughts,
            contributions=[ContributionInput(
                client_id=contribution_map[item.id], problem=item.problem,
                prior_limitation=item.prior_limitation, innovation=item.innovation,
                solution=item.solution, evidence_summary=item.evidence_summary,
                evidence_ids=item.evidence_ids,
            ) for item in response.contributions],
            experiments=[ExperimentInput(
                client_id=f"existing:{item.id}", task=item.task, datasets=item.datasets,
                baselines=item.baselines, metrics=item.metrics, result=item.result,
                conclusion=item.conclusion,
                supports_contribution_client_ids=[contribution_map[value] for value in item.contribution_ids],
                evidence_ids=item.evidence_ids,
            ) for item in response.experiments],
        )

    @staticmethod
    def source_snapshot_hash(sources: list[RAGSource]) -> str:
        canonical = [{"order": index, "source_key": source.source_key,
                      "content": " ".join(source.content.split())}
                     for index, source in enumerate(sources)]
        return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def input_hash(*, paper_id, provider_name, model, retrieval_mode, source_snapshot_hash) -> str:
        value = {"paper_id": str(paper_id), "analysis_type": "deep_reading",
                 "prompt_version": DEEP_READING_PROMPT_VERSION, "provider_name": provider_name,
                 "model": model, "retrieval_mode": retrieval_mode,
                 "source_snapshot_hash": source_snapshot_hash}
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _chunk_id(source_key: str) -> uuid.UUID | None:
        if not source_key.startswith("chunk:"):
            return None
        try:
            return uuid.UUID(source_key.split(":", 1)[1])
        except ValueError:
            return None

    @staticmethod
    def _citations_from_rag(sources: list[RAGSource]) -> list[AICitation]:
        return [AICitation(
            label=f"S{index}", source_key=source.source_key,
            source_type=source.source_type, paper_id=source.paper_id,
            paper_title=source.paper_title, document_id=source.document_id,
            note_id=source.note_id, title=source.title,
            section_title=source.section_title, page_start=source.page_start,
            page_end=source.page_end,
        ) for index, source in enumerate(sources, 1)]

    @staticmethod
    def _citation_from_snapshot(source: AIAnalysisSource) -> AICitation:
        return AICitation(
            label=f"S{source.order_index + 1}", source_key=source.source_key,
            source_type="paper_chunk", paper_id=source.paper_id,
            paper_title=source.title, document_id=source.document_id,
            title=source.title, section_title=source.section_title,
            page_start=source.page_start, page_end=source.page_end,
        )
