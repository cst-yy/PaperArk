"""Domain-level exceptions for the service layer.

The Service layer raises these instead of HTTPException.
The API layer (or a global exception handler) converts them to HTTP responses.

This keeps the Service free of FastAPI/HTTP concerns.
"""


class DomainError(Exception):
    """Base class for all business-logic errors."""

    def __init__(self, message: str = "", *, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


# ── Paper ──

class PaperNotFoundError(DomainError):
    """Raised when a paper is not found or doesn't belong to the user."""


class DuplicatePaperError(DomainError):
    """Raised when a paper with the same DOI/arXiv ID/title+year already exists."""

    def __init__(self, existing_title: str):
        super().__init__(
            f"A paper with the same identifier already exists: {existing_title}"
        )
        self.existing_title = existing_title


# ── Tag / Folder ──

class TagNotFoundError(DomainError):
    """Raised when a tag doesn't exist or belongs to another user."""


class DuplicateTagError(DomainError):
    """Raised when a user already has a tag with the same normalized name."""


class FolderNotFoundError(DomainError):
    """Raised when a folder doesn't exist or belongs to another user."""


class InvalidTagError(DomainError):
    """Raised when one or more tags don't exist or belong to another user."""


class InvalidKeywordError(DomainError):
    """Raised when one or more keywords don't exist or belong to another user."""


class InvalidFolderError(DomainError):
    """Raised when one or more folders don't exist or belong to another user."""


# ── File / Storage ──

class InvalidFileTypeError(DomainError):
    """Raised when an uploaded file is not a valid PDF."""


class FileTooLargeError(DomainError):
    """Raised when an uploaded file exceeds the size limit."""


class StorageError(DomainError):
    """Raised when a storage operation fails (disk write, etc.)."""


# ── Document ──

class DocumentNotFoundError(DomainError):
    """Raised when a document is not found or doesn't belong to the user."""


class DocumentFileNotFoundError(DomainError):
    """Raised when the document record exists but the physical file is missing."""


# ── Annotation ──

class AnnotationNotFoundError(DomainError):
    """Raised when an annotation is not found or doesn't belong to the user."""


class InvalidAnnotationError(DomainError):
    """Raised when annotation anchors or ownership are invalid."""
