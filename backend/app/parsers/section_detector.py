"""Conservative document-structure detection built only from ParsedDocument."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.parsers.base import ParsedDocument, ParsedTextBlock

_NUMBERED_HEADING = re.compile(
    # Keep Roman section numbers conservative.  Supporting C/L/D/M here made
    # bibliography lines such as ``C. Xu, ...`` look like section headings and
    # split the References section at an author's initial.
    r"^(?P<number>\d+(?:\.\d+)*\.?|[IVX]+\.)\s+(?P<title>.{2,120})$",
)
_COMMON_HEADINGS = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "related_work",
    "method": "method",
    "methods": "method",
    "methodology": "method",
    "experiments": "experiment",
    "experiment": "experiment",
    "experimental results": "experiment",
    "results": "experiment",
    "discussion": "conclusion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
    "bibliography": "references",
    "appendix": "appendix",
    "acknowledgments": "other",
    "acknowledgements": "other",
}
_REFERENCE_END = re.compile(
    r"^(?:(?:neurips|iclr|conference)\s+)?paper checklist$|^supplement(?:ary material)?$|^appendix(?:\s+[a-z0-9]+)?$|^author (?:biography|biographies)$",
    re.IGNORECASE,
)
_AUTHOR_BIO_START = re.compile(
    r"^[A-Z][A-Za-z .'-]{1,80}\s+received the (?:B\.?S\.?|M\.?S\.?|Ph\.?D\.?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TextFragment:
    page_number: int
    text: str


@dataclass
class DetectedSection:
    id: uuid.UUID
    parent_id: uuid.UUID | None
    title: str
    section_type: str
    level: int
    order_index: int
    page_start: int
    page_end: int
    fragments: list[TextFragment] = field(default_factory=list)

    @property
    def raw_text(self) -> str:
        return "\n".join(fragment.text for fragment in self.fragments).strip()


class SectionDetector:
    """Detect conservative Paper sections and preserve source page attribution."""

    def detect(self, parsed: ParsedDocument) -> list[DetectedSection]:
        if not any(page.text.strip() for page in parsed.pages):
            return []

        sections: list[DetectedSection] = []
        current: DetectedSection | None = None
        stack: list[DetectedSection] = []

        for page in parsed.pages:
            for raw_line in page.text.splitlines():
                line = " ".join(raw_line.split())
                if not line:
                    continue
                # Inside a bibliography, ordinary heading-like words and author
                # initials are reference content. Only explicit post-bibliography
                # boundaries may end it.
                heading = self._reference_end_heading(line) if current and current.section_type == "references" else self._heading_for(line, page.blocks)
                if heading:
                    title, level, section_type = heading
                    while stack and stack[-1].level >= level:
                        stack.pop()
                    parent = stack[-1] if stack else None
                    current = DetectedSection(
                        id=uuid.uuid4(),
                        parent_id=parent.id if parent else None,
                        title=title,
                        section_type=section_type,
                        level=level,
                        order_index=len(sections),
                        page_start=page.page_number,
                        page_end=page.page_number,
                    )
                    sections.append(current)
                    stack.append(current)
                    continue
                if current is not None:
                    current.fragments.append(TextFragment(page.page_number, line))

        if not sections:
            return [
                DetectedSection(
                    id=uuid.uuid4(),
                    parent_id=None,
                    title="Full Text",
                    section_type="other",
                    level=1,
                    order_index=0,
                    page_start=1,
                    page_end=parsed.page_count,
                    fragments=[
                        TextFragment(page.page_number, page.text.strip())
                        for page in parsed.pages
                        if page.text.strip()
                    ],
                )
            ]

        for index, section in enumerate(sections):
            next_start = sections[index + 1].page_start if index + 1 < len(sections) else parsed.page_count
            section.page_end = max(section.page_start, next_start - (1 if index + 1 < len(sections) else 0))
        return sections

    def _heading_for(
        self, line: str, page_blocks: list[ParsedTextBlock]
    ) -> tuple[str, int, str] | None:
        if len(line) > 140 or len(line.split()) > 18 or line.endswith((".", ",", ";", ":")):
            return None
        if re.search(r"\b(?:question|answer|guidelines|justification)\s*:", line, re.IGNORECASE):
            return None
        if re.match(r"^\d+\s*[A-Z]{2,}[A-Za-z]*$", line):
            return None
        normalized = line.casefold().rstrip(".")
        if normalized in _COMMON_HEADINGS:
            return line, 1, _COMMON_HEADINGS[normalized]

        numbered = _NUMBERED_HEADING.match(line)
        if numbered:
            number = numbered.group("number").rstrip(".")
            title = numbered.group("title").strip()
            level = number.count(".") + 1
            return line, level, self._classify(title)

        # Typography is intentionally not sufficient on its own. Cover titles,
        # author affiliations, captions, and review checklists frequently use the
        # same visual treatment as headings. Keep it as future evidence, while v1
        # accepts only semantic/numbered/all-caps signals.
        words = line.split()
        looks_like_caps = len(line) > 4 and line.isupper() and not line.isdigit()
        # A one-token acronym/model name (for example GPT-4V) is common in prose
        # and tables; only multi-word all-caps labels remain a heading signal.
        if looks_like_caps and 2 <= len(words) <= 10:
            return line, 1, self._classify(line)
        return None

    @staticmethod
    def _classify(value: str) -> str:
        normalized = value.casefold()
        for phrase, section_type in _COMMON_HEADINGS.items():
            if phrase in normalized:
                return section_type
        return "other"

    @staticmethod
    def _reference_end_heading(line: str) -> tuple[str, int, str] | None:
        if _REFERENCE_END.match(line) or _AUTHOR_BIO_START.match(line):
            return line, 1, "other"
        return None


section_detector = SectionDetector()
