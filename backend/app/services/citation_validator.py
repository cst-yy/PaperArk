"""Validate model citation labels and map them to trusted RAG provenance."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.ai import AICitation
from app.schemas.rag import RAGSource

_CITATION_RE = re.compile(r"\[S(\d+)\]")


@dataclass(frozen=True, slots=True)
class CitationValidationResult:
    answer: str
    citations: list[AICitation]
    invalid_labels: list[str]


class CitationValidator:
    def validate(self, answer: str, sources: list[RAGSource]) -> CitationValidationResult:
        source_map = {f"S{index}": source for index, source in enumerate(sources, 1)}
        valid_labels: list[str] = []
        invalid_labels: list[str] = []
        for match in _CITATION_RE.finditer(answer):
            label = f"S{match.group(1)}"
            if label not in source_map:
                if label not in invalid_labels:
                    invalid_labels.append(label)
            elif label not in valid_labels:
                valid_labels.append(label)

        sanitized = _CITATION_RE.sub(
            lambda match: match.group(0) if f"S{match.group(1)}" in source_map else "",
            answer,
        )
        sanitized = re.sub(r"[ \t]{2,}", " ", sanitized).strip()
        citations = [self.citation_for(label, source_map[label]) for label in valid_labels]
        return CitationValidationResult(sanitized, citations, invalid_labels)

    @staticmethod
    def citation_for(label: str, source: RAGSource) -> AICitation:
        return AICitation(
            label=label,
            source_key=source.source_key,
            source_type=source.source_type,
            paper_id=source.paper_id,
            paper_title=source.paper_title,
            document_id=source.document_id,
            note_id=source.note_id,
            title=source.title,
            section_title=source.section_title,
            page_start=source.page_start,
            page_end=source.page_end,
        )
