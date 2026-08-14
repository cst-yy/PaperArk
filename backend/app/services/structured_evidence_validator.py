from __future__ import annotations

import re

from app.core.exceptions import StructuredGenerationError
from app.schemas.ai import AICitation
from app.schemas.deep_reading import (
    DeepReadingContribution,
    DeepReadingExperiment,
    DeepReadingPayload,
    GroundedStructuredField,
)
from app.schemas.rag import RAGSource
from app.services.citation_validator import CitationValidator

_REF_RE = re.compile(r"^S[1-9]\d*$")
_FIELD_NAMES = (
    "background", "prior_work_limitations", "research_problem", "method_summary",
    "results_summary", "conclusion", "limitations", "future_work",
)


class StructuredEvidenceValidator:
    def validate(
        self, payload: DeepReadingPayload, sources: list[RAGSource]
    ) -> tuple[DeepReadingPayload, list[AICitation]]:
        valid_labels = {f"S{index}" for index in range(1, len(sources) + 1)}
        used_labels: list[str] = []

        def refs(values: list[str]) -> tuple[list[str], bool]:
            kept: list[str] = []
            invalid = False
            for value in values:
                if not _REF_RE.fullmatch(value) or value not in valid_labels:
                    invalid = True
                elif value not in kept:
                    kept.append(value)
                    if value not in used_labels:
                        used_labels.append(value)
            return kept, invalid

        field_updates: dict[str, GroundedStructuredField] = {}
        for name in _FIELD_NAMES:
            item = getattr(payload, name)
            kept, invalid = refs(item.evidence_refs)
            insufficient = item.insufficient_evidence or not item.content.strip() or not kept or invalid
            field_updates[name] = item.model_copy(update={
                "evidence_refs": kept,
                "insufficient_evidence": insufficient,
                "grounded": bool(item.content.strip() and kept and not insufficient),
            })

        contributions: list[DeepReadingContribution] = []
        for item in payload.contributions:
            if not any(value.strip() for value in (item.problem, item.prior_limitation, item.innovation, item.solution)):
                continue
            kept, invalid = refs(item.evidence_refs)
            insufficient = item.insufficient_evidence or not kept or invalid
            contributions.append(item.model_copy(update={
                "evidence_refs": kept, "insufficient_evidence": insufficient,
                "grounded": bool(kept and not insufficient),
            }))

        known_contributions = {item.client_id for item in contributions}
        experiments: list[DeepReadingExperiment] = []
        for item in payload.experiments:
            if not any((item.task.strip(), item.result.strip(), item.conclusion.strip(), item.datasets, item.baselines, item.metrics)):
                continue
            if not set(item.supports_contribution_client_ids) <= known_contributions:
                raise StructuredGenerationError("Experiment references a dropped or unknown contribution")
            kept, invalid = refs(item.evidence_refs)
            insufficient = item.insufficient_evidence or not kept or invalid
            experiments.append(item.model_copy(update={
                "evidence_refs": kept, "insufficient_evidence": insufficient,
                "grounded": bool(kept and not insufficient),
            }))

        validated = payload.model_copy(update={
            **field_updates, "contributions": contributions, "experiments": experiments,
        })
        source_map = {f"S{index}": source for index, source in enumerate(sources, 1)}
        citations = [CitationValidator.citation_for(label, source_map[label]) for label in used_labels]
        return validated, citations
