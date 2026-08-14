"""Caption-first, conservative Figure/Table detection from parsed page geometry."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from app.parsers.base import ParsedDocument, ParsedPage, ParsedTextBlock
from app.parsers.section_detector import DetectedSection

_CAPTION_START = re.compile(
    r"^(?P<label>(?:figure|fig\.?|table|图|表)\s*(?P<number>[0-9ivx]+))"
    r"(?:(?:\s*[:：.。]\s*(?P<body_punct>.*))|(?:\s+(?P<body_plain>.*)))?$",
    re.IGNORECASE,
)
_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z][\w\s-]{1,120}$")
_SECTION_NUMBER = re.compile(r"^\d+(?:\.\d+)+\.?$")


@dataclass(frozen=True)
class DetectedElement:
    id: uuid.UUID
    section_id: uuid.UUID | None
    element_type: str
    order_index: int
    page_number: int
    label: str | None
    caption: str
    raw_text: str
    x: float | None
    y: float | None
    width: float | None
    height: float | None
    confidence: float | None


class ElementDetector:
    """Extract captions first, then associate only safe nearby visual candidates."""

    def detect(self, parsed: ParsedDocument, sections: list[DetectedSection]) -> list[DetectedElement]:
        items: list[DetectedElement] = []
        for page in parsed.pages:
            captions = self._captions(page)
            for caption in captions:
                section_id = self._section_for(sections, page.page_number)
                visual_bbox = self._visual_bbox(page, caption)
                items.append(
                    DetectedElement(
                        id=uuid.uuid4(), section_id=section_id,
                        element_type=caption["type"], order_index=len(items),
                        page_number=page.page_number, label=caption["label"],
                        caption=caption["caption"], raw_text=caption["raw"],
                        x=visual_bbox[0] if visual_bbox else None,
                        y=visual_bbox[1] if visual_bbox else None,
                        width=visual_bbox[2] if visual_bbox else None,
                        height=visual_bbox[3] if visual_bbox else None,
                        confidence=0.9 if visual_bbox else 0.65,
                    )
                )
        return items

    def _captions(self, page: ParsedPage) -> list[dict[str, object]]:
        blocks = sorted(page.blocks, key=lambda block: (block.y0, block.x0))
        captions: list[dict[str, object]] = []
        index = 0
        while index < len(blocks):
            block = blocks[index]
            match = _CAPTION_START.match(" ".join(block.text.split()))
            if not match:
                index += 1
                continue
            label = match.group("label")
            element_type = "table" if label.casefold().startswith(("table", "表")) else "figure"
            parts = [block.text.strip()]
            end = index
            # Caption continuations are only accepted while nearby, aligned, and
            # not a distinct caption or likely body paragraph.
            while end + 1 < len(blocks):
                next_block = blocks[end + 1]
                vertical_gap = next_block.y0 - blocks[end].y1
                if vertical_gap > max(14.0, block.font_size or 10.0) * 1.8:
                    break
                if abs(next_block.x0 - block.x0) > page.width * 0.16:
                    break
                next_text = " ".join(next_block.text.split())
                if _CAPTION_START.match(next_text) or _NUMBERED_HEADING.match(next_text) or _SECTION_NUMBER.match(next_text):
                    break
                if len(next_block.text.split()) > 36:
                    break
                parts.append(next_block.text.strip())
                end += 1
            raw = " ".join(parts)
            body = match.group("body_punct") or match.group("body_plain") or ""
            caption = " ".join([label, body, *parts[1:]]).strip()
            captions.append({"type": element_type, "label": label, "caption": caption, "raw": raw, "block": block})
            index = end + 1
        return captions

    @staticmethod
    def _visual_bbox(page: ParsedPage, caption: dict[str, object]) -> tuple[float, float, float, float] | None:
        """Use only a large empty-ish layout region adjacent to a caption.

        Parsed text spans are insufficient to reconstruct vector figures/tables,
        so this deliberately returns None unless a bounded region is evident.
        """
        block = caption["block"]
        assert isinstance(block, ParsedTextBlock)
        candidates = [
            visual for visual in page.visual_blocks
            if (visual.x1 - visual.x0) > page.width * 0.12
            and (visual.y1 - visual.y0) > page.height * 0.04
            and min(visual.x1, block.x1) - max(visual.x0, block.x0) > 0
        ]
        if caption["type"] == "figure":
            candidates = [visual for visual in candidates if visual.y1 <= block.y0]
        else:
            candidates = [visual for visual in candidates if visual.y0 >= block.y1]
        if not candidates:
            return None
        target = min(candidates, key=lambda visual: abs((visual.y0 + visual.y1) / 2 - (block.y0 + block.y1) / 2))
        x0, y0 = max(0.0, target.x0), max(0.0, target.y0)
        x1, y1 = min(page.width, target.x1), min(page.height, target.y1)
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0 / page.width, y0 / page.height, (x1 - x0) / page.width, (y1 - y0) / page.height)

    @staticmethod
    def _section_for(sections: list[DetectedSection], page_number: int) -> uuid.UUID | None:
        candidates = [section for section in sections if section.page_start <= page_number <= section.page_end]
        return candidates[-1].id if candidates else None
