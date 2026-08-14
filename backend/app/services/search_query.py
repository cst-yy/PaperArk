"""Normalization and plain-text snippets for the S8 search pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", re.IGNORECASE)
_ARXIV_PREFIX = re.compile(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv\s*:\s*)", re.IGNORECASE)
_DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_ARXIV = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v\d+)?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NormalizedSearchQuery:
    raw: str
    normalized: str
    tokens: tuple[str, ...]
    looks_like_doi: bool
    looks_like_arxiv: bool


class QueryNormalizer:
    @staticmethod
    def normalize(raw: str) -> NormalizedSearchQuery:
        compact = " ".join(raw.strip().split())
        normalized = compact.casefold()
        normalized = _DOI_PREFIX.sub("", normalized)
        normalized = _ARXIV_PREFIX.sub("", normalized).removesuffix(".pdf")
        return NormalizedSearchQuery(
            raw=raw,
            normalized=normalized,
            tokens=tuple(normalized.split()),
            looks_like_doi=bool(_DOI.fullmatch(normalized)),
            looks_like_arxiv=bool(_ARXIV.fullmatch(normalized)),
        )


def build_snippet(text: str, query: NormalizedSearchQuery, max_chars: int = 240) -> str:
    """Return a focused, markup-free excerpt around the first useful match."""
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    folded = compact.casefold()
    candidates = [query.normalized, *query.tokens]
    positions = [folded.find(term) for term in candidates if term and folded.find(term) >= 0]
    position = min(positions) if positions else 0
    start = max(0, position - max_chars // 3)
    end = min(len(compact), start + max_chars)
    start = max(0, end - max_chars)
    excerpt = compact[start:end].strip()
    return ("…" if start else "") + excerpt + ("…" if end < len(compact) else "")
