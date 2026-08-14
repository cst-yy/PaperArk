"""Focused tests for PDF upload validation and storage path sandboxing."""

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.exceptions import InvalidFileTypeError, StorageError
from app.core.storage import get_full_path, validate_pdf


@pytest.mark.asyncio
async def test_validate_pdf_rejects_non_pdf_magic_bytes() -> None:
    upload = UploadFile(
        filename="fake.pdf",
        file=BytesIO(b"not a PDF"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(InvalidFileTypeError):
        await validate_pdf(upload)


def test_storage_path_cannot_escape_storage_root() -> None:
    with pytest.raises(StorageError):
        get_full_path("../../outside.pdf")
