"""PDF text extraction using PyMuPDF (fitz)."""

from pathlib import Path
from dataclasses import dataclass


@dataclass
class PageContent:
    page_number: int
    text: str
    blocks: list[dict]


@dataclass
class ParsedPDF:
    page_count: int
    pages: list[PageContent]
    metadata: dict


class PDFParser:
    """Extract text and layout information from PDF files."""

    def parse(self, pdf_path: Path) -> ParsedPDF:
        import fitz

        doc = fitz.open(str(pdf_path))
        pages: list[PageContent] = []

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")

            # Extract text blocks with bounding boxes
            blocks = []
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, block_text, block_no, block_type = block
                if block_type == 0:  # text block
                    blocks.append({
                        "bbox": [x0, y0, x1, y1],
                        "text": block_text.strip(),
                        "page": page_num + 1,
                    })

            pages.append(PageContent(
                page_number=page_num + 1,
                text=text,
                blocks=blocks,
            ))

        metadata = doc.metadata or {}
        result = ParsedPDF(
            page_count=doc.page_count,
            pages=pages,
            metadata={
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "subject": metadata.get("subject"),
                "keywords": metadata.get("keywords"),
            },
        )
        doc.close()
        return result

    def extract_abstract(self, pages: list[PageContent]) -> str | None:
        """Heuristically extract the abstract from the first few pages."""
        for page in pages[:3]:
            text = page.text.lower()
            start = text.find("abstract")
            if start == -1:
                continue
            # Find the end of abstract (next section heading)
            end_markers = ["introduction", "1.", "keywords", "index terms"]
            end = len(page.text)
            for marker in end_markers:
                pos = text.find(marker, start + 8)
                if pos != -1 and pos < end:
                    end = pos
            return page.text[start:end].strip()
        return None


pdf_parser = PDFParser()
