"""Grounded AI orchestration built on the S10 RAG context contract."""
from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import PaperNotFoundError
from app.processors.embedding import EmbeddingProvider
from app.processors.generation import GenerationProvider
from app.repositories.paper_repository import PaperRepository
from app.schemas.ai import AIAnswer, PaperQARequest, PaperQAResponse, TranslationRequest, TranslationResult
from app.schemas.rag import RAGContextRequest
from app.services.citation_validator import CitationValidator
from app.services.grounded_prompt import GroundedPromptBuilder, TranslationPromptBuilder
from app.services.rag_service import RAGService
from app.services.ai_gateway import AIGateway


class AIService:
    def __init__(
        self,
        db: AsyncSession,
        generation_provider: GenerationProvider,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.db = db
        self.rag = RAGService(db, embedding_provider)
        self.papers = PaperRepository(db)
        self.generation_provider = generation_provider
        self.prompt_builder = GroundedPromptBuilder()
        self.translation_prompt_builder = TranslationPromptBuilder()
        self.citation_validator = CitationValidator()

    async def answer_paper_question(
        self, user_id: uuid.UUID, request: PaperQARequest
    ) -> PaperQAResponse:
        paper = await self.papers.get_by_id(request.paper_id, user_id)
        if paper is None:
            raise PaperNotFoundError("Paper does not exist or belongs to another user")
        answer = await self.generate_grounded_answer(
            user_id,
            RAGContextRequest(
                query=request.query,
                mode=request.retrieval_mode,
                paper_id=paper.id,
                max_sources=request.max_sources,
                token_budget=request.token_budget,
            ),
        )
        return PaperQAResponse(paper_id=paper.id, query=request.query, **answer.model_dump())

    async def translate_selection(self, request: TranslationRequest) -> TranslationResult:
        result = await self.generation_provider.generate(
            self.translation_prompt_builder.build(request.text, request.target_language),
            0.0, settings.AI_MAX_OUTPUT_TOKENS,
        )
        return TranslationResult(translated_text=result.text.strip(), source_language=None,
                                 target_language=request.target_language)

    async def translate_user_selection(self, user_id: uuid.UUID, request: TranslationRequest) -> TranslationResult:
        result, _ = await AIGateway(self.db).generate(
            user_id=user_id, feature="selection_translation", operation="translate_selection",
            messages=self.translation_prompt_builder.build(request.text, request.target_language),
            temperature=0.0, max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
            fallback_provider=self.generation_provider,
        )
        return TranslationResult(
            translated_text=result.text.strip(),
            source_language=None,
            target_language=request.target_language,
        )

    async def generate_grounded_answer(
        self, user_id: uuid.UUID, request: RAGContextRequest
    ) -> AIAnswer:
        context = await self.rag.build_context(user_id, request)
        if not context.sources:
            return AIAnswer(
                answer="The available sources do not provide enough evidence to answer this question.",
                citations=[],
                grounded=False,
                insufficient_evidence=True,
                requested_mode=context.requested_mode,
                effective_mode=context.effective_mode,
            )

        if hasattr(self, "db"):
            result, _ = await AIGateway(self.db).generate(
                user_id=user_id, feature="paper_qa", operation="answer_question",
                messages=self.prompt_builder.build(context.query, context.sources),
                temperature=settings.AI_TEMPERATURE, max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                paper_id=request.paper_id, fallback_provider=self.generation_provider,
            )
        else:  # isolated prompt/citation unit tests have no persistence layer
            result = await self.generation_provider.generate(
                self.prompt_builder.build(context.query, context.sources),
                settings.AI_TEMPERATURE, settings.AI_MAX_OUTPUT_TOKENS,
            )
        answer, declared_insufficient = self._parse_result(result.text)
        validated = self.citation_validator.validate(answer, context.sources)
        insufficient = declared_insufficient or not validated.citations
        grounded = bool(validated.citations) and not validated.invalid_labels and not insufficient
        return AIAnswer(
            answer=validated.answer,
            citations=validated.citations,
            grounded=grounded,
            insufficient_evidence=insufficient,
            requested_mode=context.requested_mode,
            effective_mode=context.effective_mode,
        )

    @staticmethod
    def _parse_result(text: str) -> tuple[str, bool]:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.removeprefix("```json").removeprefix("```")
            candidate = candidate.removesuffix("```").strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return candidate, False
        if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
            return candidate, False
        return payload["answer"].strip(), payload.get("insufficient_evidence") is True
