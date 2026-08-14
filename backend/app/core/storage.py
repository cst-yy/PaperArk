"""Storage layer — unified file system operations.

Responsibilities:
  - PDF validation (extension, content-type, magic bytes, size)
  - UUID-based file saving (no original filenames on disk)
  - Path resolution inside the storage sandbox
  - File deletion

Does NOT: contain business logic, touch the database, or know about Paper/Document.
"""

import asyncio
import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

# ── Constants ──

PDF_MAGIC_BYTES = b"%PDF-"
READ_CHUNK_SIZE = 1024 * 1024  # 1 MB


# ── Validation ──

async def validate_pdf(file: UploadFile) -> bytes:
    """Validate an uploaded PDF and return its content.

    Validation layers:
      1. Filename ends with .pdf
      2. Content-Type declares a PDF (useful, but never trusted alone)
      3. Magic bytes start with %PDF-
      4. Streamed size cap from MAX_UPLOAD_SIZE_MB

    The stream is read in 1 MB chunks and rejected once it exceeds the cap,
    rather than loading an arbitrarily large file into memory first.
    """
    from app.core.exceptions import FileTooLargeError, InvalidFileTypeError

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise InvalidFileTypeError("仅支持 PDF 文件")

    content_type = (file.content_type or "").lower()
    if content_type and "pdf" not in content_type:
        raise InvalidFileTypeError(
            f"Content-Type 必须是 application/pdf，收到: {content_type}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total = 0
    chunks: list[bytes] = []

    while chunk := await file.read(READ_CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            await file.seek(0)
            raise FileTooLargeError(
                f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content.startswith(PDF_MAGIC_BYTES):
        await file.seek(0)
        raise InvalidFileTypeError("文件内容不是有效的 PDF（缺少 %PDF- 头）")

    await file.seek(0)
    return content


# ── Hashing ──

def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ── Save ──

async def save_bytes(
    content: bytes, sub_dir: str = "pdfs", ext: str = ".pdf"
) -> Path:
    """Save bytes under a UUID filename without blocking the event loop."""
    filename = f"{uuid.uuid4().hex}{ext}"
    target_dir = settings.storage_path / sub_dir
    await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
    file_path = target_dir / filename
    await asyncio.to_thread(file_path.write_bytes, content)
    return file_path


# ── Path helpers ──

def get_relative_path(full_path: Path) -> str:
    """Return a storage-relative path; reject paths outside the sandbox."""
    from app.core.exceptions import StorageError

    root = settings.storage_path.resolve()
    target = full_path.resolve()
    try:
        return str(target.relative_to(root))
    except ValueError as exc:
        raise StorageError("文件路径不在存储目录内") from exc


def get_full_path(relative_path: str) -> Path:
    """Resolve a storage-relative path while preventing path traversal."""
    from app.core.exceptions import StorageError

    root = settings.storage_path.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise StorageError("非法存储路径") from exc
    return target


def file_exists(relative_path: str) -> bool:
    return get_full_path(relative_path).exists()


def delete_file(relative_path: str) -> bool:
    """Delete a sandboxed file. Returns False when it is already absent."""
    path = get_full_path(relative_path)
    if path.exists():
        path.unlink()
        return True
    return False
