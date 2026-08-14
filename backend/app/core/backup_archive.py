import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from app.core.checksum import sha256_file

MANIFEST_NAME = "manifest.json"
CHECKSUMS_NAME = "checksums.json"
DATABASE_DUMP_PATH = "database/database.dump"
SUPPORTED_FORMAT_VERSION = 1


class BackupArchiveError(ValueError):
    pass


def _safe_relative_path(name: str) -> Path:
    candidate = Path(name)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BackupArchiveError(f"归档包含非法路径: {name}")
    return candidate


def _archive_data_paths(staging_root: Path) -> list[Path]:
    files = [staging_root / DATABASE_DUMP_PATH]
    storage_root = staging_root / "storage"
    if storage_root.exists():
        files.extend(path for path in storage_root.rglob("*") if path.is_file())
    return sorted(files)


def build_checksums(staging_root: Path) -> dict[str, object]:
    entries: dict[str, str] = {}
    for path in _archive_data_paths(staging_root):
        entries[path.relative_to(staging_root).as_posix()] = sha256_file(path)
    return {"algorithm": "sha256", "files": entries}


def write_archive(staging_root: Path, target_tmp_path: Path) -> None:
    with zipfile.ZipFile(target_tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in staging_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(staging_root).as_posix())


def extract_archive_safely(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        for item in archive.infolist():
            relative = _safe_relative_path(item.filename)
            target = (destination / relative).resolve()
            try:
                target.relative_to(destination.resolve())
            except ValueError as exc:
                raise BackupArchiveError(f"归档路径越界: {item.filename}") from exc
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item, "r") as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def read_manifest(archive_path: Path) -> dict:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            if MANIFEST_NAME not in archive.namelist():
                raise BackupArchiveError("备份缺少 manifest.json")
            return json.loads(archive.read(MANIFEST_NAME))
    except (zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise BackupArchiveError("备份归档损坏或 manifest 无法读取") from exc


def verify_archive_checksums(archive_path: Path) -> tuple[dict, list[str]]:
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = set(archive.namelist())
            if MANIFEST_NAME not in names or CHECKSUMS_NAME not in names:
                raise BackupArchiveError("备份缺少 manifest 或 checksums")
            manifest = json.loads(archive.read(MANIFEST_NAME))
            checksums = json.loads(archive.read(CHECKSUMS_NAME))
            if checksums.get("algorithm") != "sha256":
                raise BackupArchiveError("不支持的校验算法")
            errors: list[str] = []
            for name, expected in checksums.get("files", {}).items():
                _safe_relative_path(name)
                if name not in names:
                    errors.append(f"缺少文件: {name}")
                    continue
                digest = hashlib.sha256(archive.read(name)).hexdigest()
                if digest != expected:
                    errors.append(f"SHA-256 不匹配: {name}")
            if DATABASE_DUMP_PATH not in names:
                errors.append("缺少数据库备份 database/database.dump")
            return manifest, errors
    except zipfile.BadZipFile as exc:
        raise BackupArchiveError("备份归档不是有效 ZIP 文件") from exc
