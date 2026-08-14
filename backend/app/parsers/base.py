from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ParsedTextBlock:
    text: str
    page_number: int
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float | None = None
    font_name: str | None = None
    flags: int = 0

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 16) or bool(self.font_name and "bold" in self.font_name.lower())


@dataclass(frozen=True)
class ParsedVisualBlock:
    page_number: int
    x0: float
    y0: float
    x1: float
    y1: float
    source: str


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str
    width: float
    height: float
    blocks: list[ParsedTextBlock] = field(default_factory=list)
    visual_blocks: list[ParsedVisualBlock] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedDocument:
    page_count: int
    pages: list[ParsedPage]
    metadata: dict[str, str | None]
    warnings: list[str] = field(default_factory=list)


class DocumentParser(Protocol):
    version: str

    def parse(self, pdf_path: Path) -> ParsedDocument:
        """Parse a source PDF without mutating application state."""
