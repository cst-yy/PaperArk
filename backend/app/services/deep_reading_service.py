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
from app.services.structured_evidence_validator import StructuredEvidenceValidator


class DeepReadingService:
    def __init__(self, db, generation_provider: GenerationProvider,
                 embedding_provider: EmbeddingProvider | None = None):
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

        first = await self.generation_provider.generate(
            self.prompt.build(context.sources), settings.AI_TEMPERATURE,
            settings.DEEP_READING_MAX_OUTPUT_TOKENS,
        )
        try:
            payload = self._parse(first.text)
        except StructuredGenerationError:
            repaired = await self.generation_provider.generate(
                self.prompt.repair(first.text), 0.0, settings.DEEP_READING_MAX_OUTPUT_TOKENS
            )
            payload = self._parse(repaired.text)

        validated, citations = self.evidence.validate(payload, context.sources)
        return DeepReadingDraft(
            **validated.model_dump(), paper_id=request.paper_id,
            requested_mode=context.requested_mode, effective_mode=context.effective_mode,
            sources=citations, source_count=len(citations),
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
