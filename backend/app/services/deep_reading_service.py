from __future__ import annotations

import json
import uuid

from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import StructuredGenerationError
from app.processors.embedding import EmbeddingProvider
from app.processors.generation import GenerationProvider
from app.schemas.deep_reading import (
    DeepReadingDraft,
    DeepReadingPayload,
    DeepReadingRequest,
    GroundedStructuredField,
)
from app.services.deep_reading_prompt import DeepReadingPromptBuilder
from app.services.deep_reading_retrieval import DeepReadingRetrievalService
from app.services.ai_analysis_service import AIAnalysisService
from app.services.structured_evidence_validator import StructuredEvidenceValidator
from app.services.ai_gateway import AIGateway


class DeepReadingService:
    def __init__(self, db, generation_provider: GenerationProvider,
                 embedding_provider: EmbeddingProvider | None = None):
        self.db = db
        self.retrieval = DeepReadingRetrievalService(db, embedding_provider)
        self.generation_provider = generation_provider
        self.prompt = DeepReadingPromptBuilder()
        self.evidence = StructuredEvidenceValidator()

    async def generate(
        self, user_id: uuid.UUID, request: DeepReadingRequest
    ) -> DeepReadingDraft:
        context = await self.retrieval.retrieve(user_id, request.paper_id, request.retrieval_mode)
        if not context.sources:
            payload = self._empty_payload()
            return DeepReadingDraft(
                **payload.model_dump(), paper_id=request.paper_id,
                requested_mode=context.requested_mode, effective_mode=context.effective_mode,
                sources=[], source_count=0,
            )

        final_result, _ = await AIGateway(self.db).generate(
            user_id=user_id, feature="deep_reading", operation="structured_analysis",
            messages=self.prompt.build(context.sources), temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.DEEP_READING_MAX_OUTPUT_TOKENS, paper_id=request.paper_id,
            fallback_provider=self.generation_provider,
        )
        try:
            payload = self._parse(final_result.text)
        except StructuredGenerationError:
            final_result, _ = await AIGateway(self.db).generate(
                user_id=user_id, feature="deep_reading", operation="repair_structured_analysis",
                messages=self.prompt.repair(final_result.text), temperature=0.0,
                max_tokens=settings.DEEP_READING_MAX_OUTPUT_TOKENS, paper_id=request.paper_id,
                fallback_provider=self.generation_provider,
            )
            payload = self._parse(final_result.text)

        validated, _ = self.evidence.validate(payload, context.sources)
        return await AIAnalysisService(self.db).save_deep_reading(
            user_id=user_id, paper_id=request.paper_id, payload=validated,
            sources=context.sources, requested_mode=context.requested_mode,
            effective_mode=context.effective_mode,
            provider_name=getattr(self.generation_provider, "provider_name", "unknown"),
            model=final_result.model,
        )

    @staticmethod
    def _parse(text: str) -> DeepReadingPayload:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.removeprefix("```json").removeprefix("```")
            candidate = candidate.removesuffix("```").strip()
        try:
            return DeepReadingPayload.model_validate(json.loads(candidate))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise StructuredGenerationError("Structured generation did not match the draft contract") from exc

    @staticmethod
    def _empty_payload() -> DeepReadingPayload:
        empty = GroundedStructuredField(content="", evidence_refs=[], insufficient_evidence=True)
        return DeepReadingPayload(
            background=empty, prior_work_limitations=empty, research_problem=empty,
            method_summary=empty, results_summary=empty, conclusion=empty,
            limitations=empty, future_work=empty, contributions=[], experiments=[],
        )
