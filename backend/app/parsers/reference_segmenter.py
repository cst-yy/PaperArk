"""Deterministic bibliography entry segmentation from detected References sections."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.parsers.section_detector import DetectedSection

_NUMBERED_STARTER = re.compile(r"^\s*(?:\[(?P<bracket>\d+)\]|(?P<plain>\d{1,4})[.)])\s+(?P<body>.+)$")
_AUTHOR_YEAR_STARTER = re.compile(
    r"^(?P<author>[A-ZÀ-ÖØ-Þ][\w'’.-]+(?:,\s*[A-Z][\w.'’-]*)?(?:\s+(?:and|&|,|et al\.)\s+.+?)?)\s*[,(].{0,120}?\b(?:18|19|20)\d{2}[a-z]?\b",
    re.IGNORECASE,
)
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?\d{1,4}$", re.IGNORECASE)
_FLAT_AUTHOR_YEAR_START = re.compile(
    r"(?:^|(?<=\.)\s+)(?P<start>[A-ZÀ-ÖØ-Þ][\w'’.-]+(?:\s+[A-ZÀ-ÖØ-Þ][\w'’.-]+)*,\s+(?:[A-Z](?:-[A-Z])?\.)+)",
)
_PARENTHESIZED_YEAR = re.compile(r"\((?:18|19|20)\d{2}[a-z]?\)\.", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceCandidate:
    order_index: int
    raw_text: str
    page_start: int
    page_end: int
    section_id: object | None


class ReferenceSegmenter:
    """Split one or more ``references`` sections without reopening the PDF."""

    def segment(self, sections: list[DetectedSection]) -> list[ReferenceCandidate]:
        candidates: list[ReferenceCandidate] = []
        for section in sections:
            if section.section_type != "references":
                continue
            candidates.extend(self._segment_section(section, len(candidates)))
        return candidates

    def _segment_section(
        self, section: DetectedSection, start_index: int
    ) -> list[ReferenceCandidate]:
        # Numbered bibliographies often contain venue/year lines that look like
        # abbreviated author-year citations. Once a section uses numbering, that
        # explicit marker is the only safe entry boundary.
        uses_numbered_starters = any(
            _NUMBERED_STARTER.match(" ".join(fragment.text.split()))
            for fragment in section.fragments
        )
        entries: list[tuple[int, int, list[str]]] = []
        current_page: int | None = None
        current_end_page: int | None = None
        current_lines: list[str] = []

        for fragment in section.fragments:
            line = " ".join(fragment.text.split())
            if not line or self._is_noise(line):
                continue
            starter = self._starter_body(line, allow_author_year=not uses_numbered_starters)
            if starter is not None:
                if current_lines and current_page is not None and current_end_page is not None:
                    entries.append((current_page, current_end_page, current_lines))
                current_page = fragment.page_number
                current_end_page = fragment.page_number
                current_lines = [starter]
            elif current_lines:
                current_end_page = fragment.page_number
                current_lines.append(line)

        if current_lines and current_page is not None and current_end_page is not None:
            entries.append((current_page, current_end_page, current_lines))

        results: list[ReferenceCandidate] = []
        for offset, (entry_start_page, entry_end_page, lines) in enumerate(entries):
            raw_text = " ".join(lines).strip()
            if not raw_text:
                continue
            results.append(
                ReferenceCandidate(
                    order_index=start_index + offset,
                    raw_text=raw_text,
                    page_start=entry_start_page,
                    page_end=entry_end_page,
                    section_id=section.id,
                )
            )
        # Some publisher PDFs expose every bibliography word as an individual
        # text line. The line-oriented fallback then sees only one or two
        # starters. Reconstruct the stream and split at sentence-boundary
        # author-year starters; keep whichever deterministic strategy finds
        # more real entries.
        meaningful_fragments = [" ".join(item.text.split()) for item in section.fragments if item.text.strip()]
        is_highly_fragmented = bool(meaningful_fragments) and (
            sum(len(item.split()) <= 2 for item in meaningful_fragments) / len(meaningful_fragments) >= 0.75
        )
        if not uses_numbered_starters and is_highly_fragmented and len(results) <= 2:
            flattened = self._segment_flat_author_year(section, start_index)
            if len(flattened) > len(results):
                return flattened
        return results

    def _segment_flat_author_year(self, section: DetectedSection, start_index: int) -> list[ReferenceCandidate]:
        pieces: list[str] = []
        offsets: list[tuple[int, int]] = []
        length = 0
        for fragment in section.fragments:
            value = " ".join(fragment.text.split())
            if not value or self._is_noise(value):
                continue
            if pieces:
                length += 1
            offsets.append((length, fragment.page_number))
            pieces.append(value)
            length += len(value)
        text = " ".join(pieces).strip()
        if not text:
            return []

        starts = [match.start("start") for match in _FLAT_AUTHOR_YEAR_START.finditer(text)]
        valid_starts = [position for index, position in enumerate(starts)
            if _PARENTHESIZED_YEAR.search(text[position:(starts[index + 1] if index + 1 < len(starts) else len(text))])]
        results: list[ReferenceCandidate] = []
        for index, position in enumerate(valid_starts):
            end = valid_starts[index + 1] if index + 1 < len(valid_starts) else len(text)
            raw_text = text[position:end].strip()
            if not raw_text:
                continue
            page_start = self._page_at(offsets, position)
            page_end = self._page_at(offsets, max(position, end - 1))
            results.append(ReferenceCandidate(
                order_index=start_index + len(results), raw_text=raw_text,
                page_start=page_start, page_end=page_end, section_id=section.id,
            ))
        return results

    @staticmethod
    def _page_at(offsets: list[tuple[int, int]], position: int) -> int:
        page = offsets[0][1]
        for offset, candidate_page in offsets:
            if offset > position:
                break
            page = candidate_page
        return page

    @staticmethod
    def _starter_body(line: str, *, allow_author_year: bool) -> str | None:
        numbered = _NUMBERED_STARTER.match(line)
        if numbered:
            return numbered.group("body").strip()
        if allow_author_year and _AUTHOR_YEAR_STARTER.match(line):
            return line
        return None

    @staticmethod
    def _is_noise(line: str) -> bool:
        return bool(_PAGE_NUMBER.fullmatch(line))
