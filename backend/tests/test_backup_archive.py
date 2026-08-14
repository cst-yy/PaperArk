import json
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.backup_archive import BackupArchiveError, build_checksums, extract_archive_safely, verify_archive_checksums, write_archive


def make_stage(root: Path) -> Path:
    stage = root / "stage"
    (stage / "database").mkdir(parents=True)
    (stage / "storage" / "pdfs").mkdir(parents=True)
    (stage / "database" / "database.dump").write_bytes(b"PGDMP mock")
    (stage / "storage" / "pdfs" / "paper.pdf").write_bytes(b"%PDF-test")
    (stage / "manifest.json").write_text(json.dumps({
        "format": "AIResearchWorkspace",
        "format_version": 1,
        "backup_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "created_at": "2026-08-13T12:00:00Z",
        "app_version": "0.1.0",
        "backup_type": "manual",
        "database": {"engine": "postgresql", "major_version": 16, "schema_revision": "test", "dump_format": "custom"},
        "statistics": {"papers": 1, "documents": 1, "annotations": 0, "notes": 0, "pdf_files": 1},
        "storage": {"file_count": 1, "total_bytes": 9},
    }))
    (stage / "checksums.json").write_text(json.dumps(build_checksums(stage)))
    return stage


def test_archive_round_trip_and_checksums(tmp_path: Path) -> None:
    stage = make_stage(tmp_path)
    archive = tmp_path / "backup.airw"
    write_archive(stage, archive)
    manifest, errors = verify_archive_checksums(archive)
    assert manifest["format"] == "AIResearchWorkspace"
    assert errors == []


def test_archive_detects_corrupted_payload(tmp_path: Path) -> None:
    stage = make_stage(tmp_path)
    archive = tmp_path / "backup.airw"
    write_archive(stage, archive)
    extracted = tmp_path / "extracted"
    extract_archive_safely(archive, extracted)
    (extracted / "storage" / "pdfs" / "paper.pdf").write_bytes(b"tampered")
    shutil.make_archive(str(tmp_path / "tampered"), "zip", extracted)
    tampered_archive = tmp_path / "tampered.zip"
    _, errors = verify_archive_checksums(tampered_archive)
    assert any("SHA-256" in error for error in errors)


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.airw"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../../escape.txt", "nope")
    with pytest.raises(BackupArchiveError):
        extract_archive_safely(archive, tmp_path / "destination")
