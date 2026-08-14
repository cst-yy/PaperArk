"""PDF utility service for file paths, covers, and document URLs.

PDF serving itself is owned by DocumentService and the
/api/documents/{document_id}/file endpoint.
"""

from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.core.storage import get_full_path


class PDFService:
    def get_pdf_path(self, relative_path: str) -> Path:
        """Get the full filesystem path for a stored PDF."""
        return get_full_path(relative_path)

    def get_pdf_url(self, document_id: UUID) -> str:
        """Get the current API URL for serving a Document PDF inline."""
        return f"/api/documents/{document_id}/file"

    async def generate_cover(self, pdf_path: Path) -> str | None:
        """Generate a cover image from the first page of a PDF."""
        try:
            import fitz  # PyMuPDF

            with fitz.open(str(pdf_path)) as doc:
                if doc.page_count > 0:
                    page = doc[0]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    cover_dir = settings.storage_path / "covers"
                    cover_dir.mkdir(parents=True, exist_ok=True)
                    cover_path = cover_dir / f"{pdf_path.stem}.png"
                    pix.save(str(cover_path))
                    from app.core.storage import get_relative_path
                    return get_relative_path(cover_path)
        except Exception:
            pass
        return None

    def get_page_count(self, pdf_path: Path) -> int:
        """Get the number of pages in a PDF."""
        try:
            import fitz
            with fitz.open(str(pdf_path)) as doc:
                return doc.page_count
        except Exception:
            return 0


pdf_service = PDFService()
