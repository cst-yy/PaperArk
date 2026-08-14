from pathlib import Path

import fitz

from app.parsers.base import ParsedDocument, ParsedPage, ParsedTextBlock, ParsedVisualBlock


class PDFParser:
    """PyMuPDF-backed source-text parser with no database dependencies."""

    version = "pdf-parser-v1"

    def parse(self, pdf_path: Path) -> ParsedDocument:
        warnings: list[str] = []
        pages: list[ParsedPage] = []

        with fitz.open(str(pdf_path)) as pdf:
            for index, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                if not text:
                    warnings.append(f"第 {index} 页未检测到可提取文本，可能是扫描页或图片页。")
                rect = page.rect
                pages.append(
                    ParsedPage(
                        page_number=index,
                        text=text,
                        width=float(rect.width),
                        height=float(rect.height),
                        blocks=self._extract_text_blocks(page, index),
                        visual_blocks=self._extract_visual_blocks(page, index),
                    )
                )

            metadata = pdf.metadata or {}
            return ParsedDocument(
                page_count=pdf.page_count,
                pages=pages,
                metadata={
                    "title": metadata.get("title"),
                    "author": metadata.get("author"),
                    "subject": metadata.get("subject"),
                    "keywords": metadata.get("keywords"),
                },
                warnings=warnings,
            )

    @staticmethod
    def _extract_visual_blocks(page, page_number: int) -> list[ParsedVisualBlock]:
        visuals: list[ParsedVisualBlock] = []
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect and rect.width > 20 and rect.height > 20:
                visuals.append(ParsedVisualBlock(page_number, float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1), "vector"))
        for image in page.get_image_info(xrefs=True):
            rect = image.get("bbox")
            if rect and rect[2] - rect[0] > 20 and rect[3] - rect[1] > 20:
                visuals.append(ParsedVisualBlock(page_number, float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]), "image"))
        return visuals

    @staticmethod
    def _extract_text_blocks(page, page_number: int) -> list[ParsedTextBlock]:
        blocks: list[ParsedTextBlock] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            fallback_bbox = block.get("bbox", (0, 0, 0, 0))
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    value = (span.get("text") or "").strip()
                    if not value:
                        continue
                    x0, y0, x1, y1 = span.get("bbox", fallback_bbox)
                    blocks.append(
                        ParsedTextBlock(
                            text=value,
                            page_number=page_number,
                            x0=float(x0),
                            y0=float(y0),
                            x1=float(x1),
                            y1=float(y1),
                            font_size=float(span.get("size", 0)) or None,
                            font_name=span.get("font"),
                            flags=int(span.get("flags", 0)),
                        )
                    )
        return blocks
