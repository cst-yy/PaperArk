"""Stable page-region derivation used by translation and citation navigation."""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from app.parsers.base import ParsedDocument, ParsedTextBlock


@dataclass(frozen=True, slots=True)
class DetectedPageBlock:
    id: uuid.UUID
    page_number: int
    block_order: int
    reading_order: int
    block_type: str
    name: str
    is_default: bool
    column_index: int | None
    bounding_box: dict[str, float]
    source_text: str
    normalized_text: str
    source_hash: str


class PageBlockDetector:
    version = "page-block-v1"
    _heading = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][^.!?]{0,100}$")

    def detect(self, parsed: ParsedDocument) -> list[DetectedPageBlock]:
        result: list[DetectedPageBlock] = []
        for page in parsed.pages:
            source_text = page.text.strip()
            normalized = " ".join(source_text.split())
            source_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            result.append(DetectedPageBlock(
                id=uuid.uuid4(), page_number=page.page_number,
                block_order=0, reading_order=page.page_number - 1, block_type="page",
                name="整页", is_default=True, column_index=None,
                bounding_box={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                source_text=source_text, normalized_text=normalized, source_hash=source_hash,
            ))
        return result

    def _merge(self, blocks: list[ParsedTextBlock], width: float) -> list[ParsedTextBlock]:
        """Merge PDF spans into readable lines/paragraphs without crossing columns."""
        spans = sorted(blocks, key=lambda b: (self._column(b, width) if self._column(b, width) is not None else -1, b.y0, b.x0))
        lines: list[ParsedTextBlock] = []
        for span in spans:
            previous = lines[-1] if lines else None
            same_column = previous is not None and self._column(previous, width) == self._column(span, width)
            tolerance = max(2.0, (span.font_size or 10) * .35)
            if previous and same_column and abs(previous.y0 - span.y0) <= tolerance:
                lines[-1] = ParsedTextBlock(text=f"{previous.text} {span.text}", page_number=span.page_number,
                    x0=min(previous.x0, span.x0), y0=min(previous.y0, span.y0), x1=max(previous.x1, span.x1),
                    y1=max(previous.y1, span.y1), font_size=max(previous.font_size or 0, span.font_size or 0) or None,
                    font_name=previous.font_name, flags=previous.flags | span.flags)
            else:
                lines.append(span)
        paragraphs: list[ParsedTextBlock] = []
        for line in lines:
            previous = paragraphs[-1] if paragraphs else None
            gap = line.y0 - previous.y1 if previous else 999
            same_column = previous is not None and self._column(previous, width) == self._column(line, width)
            previous_is_heading = previous is not None and self._heading.match(previous.text) and (previous.is_bold or (previous.font_size or 0) >= 13)
            can_join = previous is not None and same_column and 0 <= gap <= max(4, (line.font_size or 10) * .8) and not previous_is_heading
            if can_join:
                paragraphs[-1] = ParsedTextBlock(text=f"{previous.text} {line.text}", page_number=line.page_number,
                    x0=min(previous.x0, line.x0), y0=previous.y0, x1=max(previous.x1, line.x1), y1=line.y1,
                    font_size=previous.font_size, font_name=previous.font_name, flags=previous.flags | line.flags)
            else:
                paragraphs.append(line)
        return paragraphs

    @staticmethod
    def _column(block: ParsedTextBlock, width: float) -> int | None:
        center = (block.x0 + block.x1) / 2
        if block.x0 < width * .15 and block.x1 > width * .85:
            return None
        return 0 if center < width / 2 else 1

    def _type(self, block: ParsedTextBlock, text: str, height: float) -> str:
        lower = text.lower()
        if block.y0 < height * .05:
            return "header"
        if block.y1 > height * .95:
            return "footer"
        if lower.startswith(("figure ", "fig. ")):
            return "figure_caption"
        if lower.startswith("table "):
            return "table_caption"
        if self._heading.match(text) and len(text.split()) <= 14 and (block.is_bold or (block.font_size or 0) >= 13):
            return "heading"
        if re.fullmatch(r"\[?\d+(?:\)|\]).*", text) and len(text) < 250:
            return "list"
        return "paragraph"
