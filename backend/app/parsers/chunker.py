"""Section-aware paragraph chunking for S7-B."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from app.parsers.section_detector import DetectedSection, TextFragment


@dataclass(frozen=True)
class DerivedChunk:
    id: uuid.UUID
    section_id: uuid.UUID
    order_index: int
    content: str
    page_start: int
    page_end: int
    token_count: int
    char_count: int


class SectionChunker:
    """Split one Section at a time; overlap never crosses Section boundaries."""

    def __init__(self, target_tokens: int = 700, max_tokens: int = 1000, overlap_tokens: int = 80):
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, sections: list[DetectedSection]) -> list[DerivedChunk]:
        chunks: list[DerivedChunk] = []
        for section in sections:
            paragraphs = self._paragraphs(section.fragments)
            buffer: list[tuple[int, str]] = []
            for page, paragraph in paragraphs:
                pieces = self._split_long_paragraph(paragraph)
                for piece in pieces:
                    candidate = "\n\n".join(text for _, text in buffer + [(page, piece)])
                    if buffer and self._estimated_tokens(candidate) > self.target_tokens:
                        chunks.append(self._build(section, len(chunks), buffer))
                        overlap = self._tail_overlap(buffer)
                        buffer = overlap + [(page, piece)]
                    else:
                        buffer.append((page, piece))
            if buffer:
                chunks.append(self._build(section, len(chunks), buffer))
        return chunks

    @staticmethod
    def _paragraphs(fragments: list[TextFragment]) -> list[tuple[int, str]]:
        paragraphs: list[tuple[int, str]] = []
        for fragment in fragments:
            for paragraph in re.split(r"\n\s*\n", fragment.text):
                value = " ".join(paragraph.split())
                if value:
                    paragraphs.append((fragment.page_number, value))
        return paragraphs

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        if self._estimated_tokens(paragraph) <= self.max_tokens:
            return [paragraph]
        sentences = re.split(r"(?<=[.!?。！？])\s+", paragraph)
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            if current and self._estimated_tokens(f"{current} {sentence}") > self.max_tokens:
                pieces.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            pieces.append(current)
        return pieces or [paragraph]

    def _tail_overlap(self, buffer: list[tuple[int, str]]) -> list[tuple[int, str]]:
        if not self.overlap_tokens:
            return []
        result: list[tuple[int, str]] = []
        for item in reversed(buffer):
            result.insert(0, item)
            if self._estimated_tokens(" ".join(text for _, text in result)) >= self.overlap_tokens:
                break
        return result

    def _build(self, section: DetectedSection, order: int, parts: list[tuple[int, str]]) -> DerivedChunk:
        content = "\n\n".join(text for _, text in parts).strip()
        return DerivedChunk(
            id=uuid.uuid4(), section_id=section.id, order_index=order, content=content,
            page_start=min(page for page, _ in parts), page_end=max(page for page, _ in parts),
            token_count=self._estimated_tokens(content), char_count=len(content),
        )

    @staticmethod
    def _estimated_tokens(value: str) -> int:
        return max(1, len(re.findall(r"[\w]+|[^\s\w]", value)))


section_chunker = SectionChunker()
