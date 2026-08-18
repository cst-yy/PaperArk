"""Best-effort, offline metadata extraction for bibliography entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.parsers.reference_segmenter import ReferenceCandidate

_DOI = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi\s*[:.]?\s*)?(10\.\d{4,9}/[-._;()/:a-z0-9]+)", re.IGNORECASE)
_ARXIV = re.compile(r"(?:arxiv(?:\.org/(?:abs|pdf)/)?\s*[:/]?\s*)(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)
_YEAR = re.compile(r"\b((?:18|19|20)\d{2})[a-z]?\b")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ParsedReference:
    order_index: int
    raw_text: str
    page_start: int
    page_end: int
    section_id: object | None
    title: str | None
    authors: list[str] | None
    year: int | None
    doi: str | None
    arxiv_id: str | None
    venue: str | None


def normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    match = _DOI.search(raw.strip())
    if not match:
        return None
    return match.group(1).rstrip(".,;:)]}").lower()


def normalize_arxiv_id(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip()
    if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", cleaned, re.IGNORECASE):
        return cleaned.lower()
    match = _ARXIV.search(cleaned)
    return match.group(1).lower() if match else None


class ReferenceMetadataParser:
    """Parse reliable identifiers first; all human-readable fields are optional."""

    def parse(self, candidate: ReferenceCandidate) -> ParsedReference:
        text = candidate.raw_text
        doi = normalize_doi(text)
        arxiv_id = normalize_arxiv_id(text)
        year = self._year(text)
        title, authors, venue = self._human_fields(text, year)
        return ParsedReference(
            order_index=candidate.order_index,
            raw_text=text,
            page_start=candidate.page_start,
            page_end=candidate.page_end,
            section_id=candidate.section_id,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            arxiv_id=arxiv_id,
            venue=venue,
        )

    @staticmethod
    def _year(text: str) -> int | None:
        current_upper = datetime.now(timezone.utc).year + 1
        values = [int(value) for value in _YEAR.findall(text) if 1800 <= int(value) <= current_upper]
        return values[-1] if values else None

    def _human_fields(self, text: str, year: int | None) -> tuple[str | None, list[str] | None, str | None]:
        cleaned = _DOI.sub("", text)
        cleaned = _ARXIV.sub("", cleaned)
        # Keep common initial-based author names (for example "A. Author")
        # together before sentence splitting; otherwise a title heuristic would
        # fabricate metadata from fragmented author tokens.
        cleaned = re.sub(r"\b([A-Z])\.\s+(?=[A-Z])", lambda match: f"{match.group(1)}.\u00a0", cleaned)
        parts = [part.strip(" .;,:").replace("\u00a0", " ") for part in _SENTENCE.split(cleaned) if part.strip(" .;,: ")]
        if len(parts) < 2:
            return None, None, None

        year_index = next((index for index, part in enumerate(parts) if _YEAR.search(part)), None)
        author_part = parts[0]
        title_candidates = parts[1:] if year_index is None else parts[year_index + 1 :]
        if year_index is not None and year_index > 0:
            author_part = " ".join(parts[:year_index])
        title = next((part for part in title_candidates if self._looks_like_title(part)), None)
        if title is None and len(parts) >= 3 and self._looks_like_title(parts[1]):
            title = parts[1]
        authors = self._authors(author_part)
        venue = self._venue(parts, title)
        return title, authors, venue

    @staticmethod
    def _looks_like_title(value: str) -> bool:
        words = value.split()
        return 3 <= len(words) <= 40 and not value.casefold().startswith(("in ", "proceedings", "vol ", "pp "))

    @staticmethod
    def _authors(value: str) -> list[str] | None:
        normalized = re.sub(r"\bet al\.?", "", value, flags=re.IGNORECASE).strip(" ,;")
        pieces = [piece.strip() for piece in re.split(r"\s+(?:and|&)\s+|;", normalized) if piece.strip()]
        return pieces or None

    @staticmethod
    def _venue(parts: list[str], title: str | None) -> str | None:
        if not title:
            return None
        try:
            index = parts.index(title)
        except ValueError:
            return None
        for part in parts[index + 1 :]:
            if len(part) >= 3 and not _YEAR.fullmatch(part):
                return part[:500]
        return None
