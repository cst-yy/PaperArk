from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.processors.embedding import EmbeddingProvider
from app.schemas.rag import RAGMode, RAGSource
from app.services.rag_context import RAGCandidate, RAGContextAssembler
from app.services.rag_retrieval import RAGRetrievalService


DEEP_READING_INTENTS = (
    "background OR motivation OR introduction OR challenge",
    '"research problem" OR objective OR problem',
    "method OR framework OR architecture OR algorithm OR approach",
    "contribution OR innovation OR novelty",
    "experiment OR evaluation OR dataset OR baseline OR metric",
    "result OR performance OR ablation OR comparison",
    "limitation OR weakness OR discussion OR future",
    "conclusion OR summary",
)


@dataclass(frozen=True, slots=True)
class DeepReadingContext:
    sources: list[RAGSource]
    requested_mode: RAGMode
    effective_mode: RAGMode
    estimated_tokens: int
    truncated: bool


class DeepReadingRetrievalService:
    def __init__(self, db, provider: EmbeddingProvider | None = None):
        self.retrieval = RAGRetrievalService(db, provider)
        self.assembler = RAGContextAssembler()

    async def retrieve(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, mode: RAGMode
    ) -> DeepReadingContext:
        intent_results: list[list[RAGCandidate]] = []
        effective_modes: list[str] = []
        for query in DEEP_READING_INTENTS:
            candidates, effective, _, _ = await self.retrieval.retrieve(
                user_id, query, mode, paper_id
            )
            intent_results.append([item for item in candidates if item.source_type == "paper_chunk"])
            effective_modes.append(effective)

        diverse = self._round_robin_with_section_cap(intent_results)
        sources, _, tokens, truncated = self.assembler.assemble(
            diverse,
            max_sources=settings.DEEP_READING_MAX_SOURCES,
            token_budget=settings.DEEP_READING_CONTEXT_BUDGET,
            paper_scope=True,
        )
        effective: RAGMode = mode
        if mode == "hybrid" and any(item != "hybrid" for item in effective_modes):
            effective = "lexical"
        return DeepReadingContext(
            sources=sources,
            requested_mode=mode,
            effective_mode=effective,
            estimated_tokens=tokens,
            truncated=truncated,
        )

    @staticmethod
    def _round_robin_with_section_cap(
        intent_results: list[list[RAGCandidate]],
    ) -> list[RAGCandidate]:
        output: list[RAGCandidate] = []
        seen: set[str] = set()
        section_counts: dict[str, int] = {}
        max_length = max((len(items) for items in intent_results), default=0)
        for rank in range(max_length):
            for items in intent_results:
                if rank >= len(items):
                    continue
                candidate = items[rank]
                if candidate.source_key in seen:
                    continue
                section_key = str(candidate.section_id or f"{candidate.document_id}:{candidate.section_title or 'unknown'}")
                if section_counts.get(section_key, 0) >= settings.DEEP_READING_SECTION_SOURCE_CAP:
                    continue
                seen.add(candidate.source_key)
                section_counts[section_key] = section_counts.get(section_key, 0) + 1
                output.append(candidate)
        return output
