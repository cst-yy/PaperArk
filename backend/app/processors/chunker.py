"""Text chunker - splits document content into RAG-ready chunks."""

from dataclasses import dataclass

from app.core.config import settings
from app.processors.pdf_parser import PageContent
from app.processors.structure_parser import ParsedSection


@dataclass
class TextChunk:
    content: str
    page_number: int | None
    chunk_index: int
    section_title: str | None = None
    token_count: int | None = None
    bbox: str | None = None


class Chunker:
    """Split text into overlapping chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(self, pages: list[PageContent]) -> list[TextChunk]:
        """Chunk text by pages with overlap."""
        chunks: list[TextChunk] = []
        chunk_idx = 0

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # Split by paragraphs first
            paragraphs = text.split("\n\n")
            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_chunk) + len(para) > self.chunk_size:
                    if current_chunk:
                        chunks.append(TextChunk(
                            content=current_chunk.strip(),
                            page_number=page.page_number,
                            chunk_index=chunk_idx,
                            token_count=len(current_chunk) // 4,
                        ))
                        chunk_idx += 1
                    # Start new chunk with overlap
                    if self.overlap > 0 and len(current_chunk) > self.overlap:
                        current_chunk = current_chunk[-self.overlap:] + "\n" + para
                    else:
                        current_chunk = para
                else:
                    current_chunk = (current_chunk + "\n" + para).strip()

            # Don't forget the last chunk of the page
            if current_chunk.strip():
                chunks.append(TextChunk(
                    content=current_chunk.strip(),
                    page_number=page.page_number,
                    chunk_index=chunk_idx,
                    token_count=len(current_chunk) // 4,
                ))
                chunk_idx += 1

        return chunks

    def chunk_sections(
        self, sections: list[ParsedSection]
    ) -> list[TextChunk]:
        """Chunk text by sections."""
        chunks: list[TextChunk] = []
        chunk_idx = 0

        for section in sections:
            if not section.content.strip():
                continue

            if len(section.content) <= self.chunk_size:
                chunks.append(TextChunk(
                    content=section.content.strip(),
                    page_number=section.page_start,
                    chunk_index=chunk_idx,
                    section_title=section.title,
                    token_count=len(section.content) // 4,
                ))
                chunk_idx += 1
            else:
                # Split long sections
                words = section.content.split()
                for i in range(0, len(words), self.chunk_size // 5):
                    chunk_text = " ".join(words[i:i + self.chunk_size // 5])
                    chunks.append(TextChunk(
                        content=chunk_text,
                        page_number=section.page_start,
                        chunk_index=chunk_idx,
                        section_title=section.title,
                        token_count=len(chunk_text) // 4,
                    ))
                    chunk_idx += 1

        return chunks


chunker = Chunker()
