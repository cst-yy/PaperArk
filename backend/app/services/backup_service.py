import asyncio
import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.backup_archive import (
    BackupArchiveError,
    CHECKSUMS_NAME,
    DATABASE_DUMP_PATH,
    MANIFEST_NAME,
    SUPPORTED_FORMAT_VERSION,
    build_checksums,
    extract_archive_safely,
    read_manifest,
    verify_archive_checksums,
    write_archive,
)
from app.core.checksum import sha256_file
from app.core.config import settings
from app.core.database import DEFAULT_USER_ID, engine, get_db
from app.core.workspace_lock import WorkspaceBusyError, workspace_lock
from app.models import Document
from app.services.workspace_settings_service import WorkspaceSettingsService
from app.schemas.backup import (
    BackupDatabaseInfo,
    BackupItem,
    BackupManifest,
    BackupStatistics,
    BackupStorageInfo,
    BackupVerificationResult,
    RestoreResult,
    WorkspaceInfo,
)

APP_VERSION = "0.1.0"
STORAGE_ALLOWLIST = ("pdfs", "covers", "thumbnails", "clips")


class BackupError(RuntimeError):
    pass


class BackupNotFoundError(BackupError):
    pass


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _copy_storage(source: Path, destination: Path) -> tuple[int, int]:
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0
    for directory in STORAGE_ALLOWLIST:
        source_dir = source / directory
        target_dir = destination / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        if not source_dir.exists():
            continue
        for item in source_dir.rglob("*"):
            if item.is_dir():
                continue
            relative = item.relative_to(source_dir)
            target = target_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            count += 1
            total += item.stat().st_size
    return count, total


def _database_connection_args() -> tuple[list[str], dict[str, str]]:
    parsed = urlparse(settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))
    if not parsed.hostname or not parsed.path:
        raise BackupError("DATABASE_URL 缺少数据库连接信息")
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    args = [
        "-h", parsed.hostname,
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
    ]
    return args, env


class BackupService:
    """Orchestrates portable Workspace backups and guarded restore operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @property
    def workspace_path(self) -> Path:
        return settings.workspace_path

    @property
    def backup_path(self) -> Path:
        return settings.backup_path

    async def _statistics(self) -> BackupStatistics:
        tables = ("papers", "documents", "annotations", "notes")
        counts: dict[str, int] = {}
        for table in tables:
            result = await self.db.execute(text(f"SELECT count(*) FROM {table}"))
            counts[table] = int(result.scalar_one())
        storage_files = [item for directory in STORAGE_ALLOWLIST for item in (settings.storage_path / directory).rglob("*") if item.is_file()]
        return BackupStatistics(
            papers=counts["papers"],
            documents=counts["documents"],
            annotations=counts["annotations"],
            notes=counts["notes"],
            pdf_files=sum(1 for item in storage_files if item.suffix.lower() == ".pdf"),
        )

    async def _schema_revision(self) -> str:
        result = await self.db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        return str(result.scalar_one())

    async def _backfill_document_hashes(self) -> None:
        documents = (await self.db.execute(select(Document).where(Document.file_hash.is_(None)))).scalars().all()
        changed = False
        for document in documents:
            path = settings.storage_path / document.file_path
            if path.is_file():
                document.file_hash = await asyncio.to_thread(sha256_file, path)
                changed = True
        if changed:
            await self.db.commit()

    def _workspace_metadata(self) -> dict:
        path = self.workspace_path / "workspace.json"
        if not path.is_file():
            raise BackupError("工作区缺少 workspace.json")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("format") != "AIResearchWorkspace":
                raise BackupError("workspace.json 格式不受支持")
            uuid.UUID(str(data["workspace_id"]))
            return data
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise BackupError("workspace.json 无法读取或 workspace_id 无效") from exc

    async def _run_database_command(
        self,
        command: list[str],
        *,
        include_connection: bool = True,
        timeout: int = 300,
    ) -> None:
        args, env = _database_connection_args()
        process = await asyncio.create_subprocess_exec(
            *command, *(args if include_connection else []),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise BackupError("数据库备份或恢复操作超时")
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip()
            raise BackupError(f"数据库命令失败: {message or 'unknown error'}")

    async def _dump_database(self, target: Path) -> None:
        await self._run_database_command(["pg_dump", "-Fc", "-f", str(target)])
        if not target.is_file() or target.stat().st_size == 0:
            raise BackupError("数据库备份未生成有效文件")
        await self._validate_dump(target)

    async def _validate_dump(self, dump_path: Path) -> None:
        await self._run_database_command(
            ["pg_restore", "-l", str(dump_path)],
            include_connection=False,
        )

    async def _restore_database(self, dump_path: Path) -> None:
        # Release the request session before pg_restore changes the live schema.
        await self.db.rollback()
        await self.db.close()
        await engine.dispose()
        args, env = _database_connection_args()
        process = await asyncio.create_subprocess_exec(
            "pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", *args, str(dump_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise BackupError(f"数据库命令失败: {stderr.decode('utf-8', errors='replace').strip()}")

    async def _create_backup_unlocked(self, backup_type: str) -> BackupItem:
        await self._backfill_document_hashes()
        metadata = self._workspace_metadata()
        backup_id = uuid.uuid4()
        now = datetime.now(UTC)
        staging_parent = self.backup_path / ".staging"
        staging_parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f"{backup_id}-", dir=staging_parent))
        final_name = f"AIResearchWorkspace_{now.strftime('%Y-%m-%d_%H%M%S')}_{backup_id.hex[:6]}.airw"
        final_path = self.backup_path / final_name
        tmp_archive = self.backup_path / f".{final_name}.tmp"
        try:
            database_dir = stage / "database"
            database_dir.mkdir(parents=True)
            await self._dump_database(database_dir / "database.dump")
            file_count, total_bytes = await asyncio.to_thread(_copy_storage, settings.storage_path, stage / "storage")
            manifest = BackupManifest(
                format_version=SUPPORTED_FORMAT_VERSION,
                backup_id=backup_id,
                workspace_id=uuid.UUID(str(metadata["workspace_id"])),
                created_at=now,
                app_version=APP_VERSION,
                backup_type=backup_type,
                database=BackupDatabaseInfo(
                    major_version=int(metadata.get("database", {}).get("major_version", 16)),
                    schema_revision=await self._schema_revision(),
                ),
                statistics=await self._statistics(),
                storage=BackupStorageInfo(file_count=file_count, total_bytes=total_bytes),
            )
            (stage / MANIFEST_NAME).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
            (stage / CHECKSUMS_NAME).write_text(json.dumps(build_checksums(stage), indent=2), encoding="utf-8")
            await asyncio.to_thread(write_archive, stage, tmp_archive)
            verification = await self._verify_path(tmp_archive)
            if not verification.valid:
                raise BackupError("归档校验失败: " + "; ".join(verification.errors))
            os.replace(tmp_archive, final_path)
            return BackupItem(
                backup_id=backup_id,
                filename=final_name,
                created_at=now,
                size_bytes=final_path.stat().st_size,
                format_version=manifest.format_version,
                schema_revision=manifest.database.schema_revision,
                backup_type=backup_type,
                status="verified",
                statistics=manifest.statistics,
            )
        finally:
            shutil.rmtree(stage, ignore_errors=True)
            tmp_archive.unlink(missing_ok=True)

    async def create_backup(self) -> BackupItem:
        item = await self.create_backup_of_type("manual")
        await WorkspaceSettingsService(self.db).record_verification(
            DEFAULT_USER_ID, item.backup_id, datetime.now(UTC)
        )
        return item

    async def create_backup_of_type(self, backup_type: str) -> BackupItem:
        if backup_type not in {"manual", "scheduled", "emergency"}:
            raise BackupError("不支持的备份类型")
        try:
            async with workspace_lock.exclusive():
                return await self._create_backup_unlocked(backup_type)
        except WorkspaceBusyError as exc:
            raise BackupError(str(exc)) from exc

    async def run_scheduled_backup_if_due(self) -> BackupItem | None:
        """Attempt one due scheduled backup; errors are persisted for Settings and re-raised."""
        policy_service = WorkspaceSettingsService(self.db)
        policy = await policy_service.get_backup_policy(DEFAULT_USER_ID)
        if not policy_service.is_due(policy):
            return None
        try:
            item = await self.create_backup_of_type("scheduled")
            await self.rotate_scheduled_backups(policy.retention)
            await policy_service.record_scheduled_success(DEFAULT_USER_ID, item.created_at)
            await policy_service.record_verification(DEFAULT_USER_ID, item.backup_id, datetime.now(UTC))
            return item
        except Exception as exc:
            await policy_service.record_scheduled_failure(DEFAULT_USER_ID, str(exc))
            raise

    def _backup_paths(self) -> list[Path]:
        return sorted(self.backup_path.glob("*.airw"), key=lambda item: item.stat().st_mtime, reverse=True)

    def _find_backup(self, backup_id: uuid.UUID) -> Path:
        for path in self._backup_paths():
            try:
                manifest = BackupManifest.model_validate(read_manifest(path))
                if manifest.backup_id == backup_id:
                    return path
            except (BackupArchiveError, ValueError):
                continue
        raise BackupNotFoundError("未找到指定备份")

    async def _verify_path(self, path: Path) -> BackupVerificationResult:
        try:
            manifest_data, checksum_errors = await asyncio.to_thread(verify_archive_checksums, path)
            manifest = BackupManifest.model_validate(manifest_data)
            if manifest.format_version > SUPPORTED_FORMAT_VERSION:
                return BackupVerificationResult(valid=False, status="unsupported", errors=["备份格式版本高于当前应用支持范围"], manifest=manifest)
            if checksum_errors:
                return BackupVerificationResult(valid=False, status="corrupted", errors=checksum_errors, manifest=manifest)
            with tempfile.TemporaryDirectory(prefix="airw-verify-") as temporary:
                dump_path = Path(temporary) / "database.dump"
                import zipfile
                with zipfile.ZipFile(path, "r") as archive:
                    dump_path.write_bytes(archive.read(DATABASE_DUMP_PATH))
                await self._validate_dump(dump_path)
            return BackupVerificationResult(valid=True, status="valid", manifest=manifest)
        except (BackupArchiveError, ValueError, BackupError, OSError) as exc:
            return BackupVerificationResult(valid=False, status="invalid", errors=[str(exc)])

    async def verify_backup(self, backup_id: uuid.UUID) -> BackupVerificationResult:
        try:
            async with workspace_lock.exclusive():
                result = await self._verify_path(self._find_backup(backup_id))
                policy_service = WorkspaceSettingsService(self.db)
                if result.valid:
                    await policy_service.record_verification(DEFAULT_USER_ID, backup_id, datetime.now(UTC))
                else:
                    await policy_service.record_invalid_verification(DEFAULT_USER_ID, backup_id)
                return result
        except WorkspaceBusyError as exc:
            raise BackupError(str(exc)) from exc

    async def get_backup(self, backup_id: uuid.UUID) -> BackupItem:
        path = self._find_backup(backup_id)
        manifest = BackupManifest.model_validate(read_manifest(path))
        verification = await self._verify_path(path)
        return BackupItem(
            backup_id=manifest.backup_id,
            filename=path.name,
            created_at=manifest.created_at,
            size_bytes=path.stat().st_size,
            format_version=manifest.format_version,
            schema_revision=manifest.database.schema_revision,
            backup_type=manifest.backup_type,
            status="verified" if verification.valid else "invalid",
            statistics=manifest.statistics,
        )

    async def rotate_scheduled_backups(self, keep: int) -> None:
        """Retention contract for future scheduling; manual/emergency archives are never removed."""
        if keep < 1:
            raise BackupError("scheduled backup 保留数量至少为 1")
        scheduled = [item for item in await self.list_backups() if item.backup_type == "scheduled"]
        for item in scheduled[keep:]:
            self._find_backup(item.backup_id).unlink()

    async def list_backups(self) -> list[BackupItem]: 
        items: list[BackupItem] = []
        for path in self._backup_paths():
            try:
                manifest = BackupManifest.model_validate(read_manifest(path))
                items.append(BackupItem(
                    backup_id=manifest.backup_id,
                    filename=path.name,
                    created_at=manifest.created_at,
                    size_bytes=path.stat().st_size,
                    format_version=manifest.format_version,
                    schema_revision=manifest.database.schema_revision,
                    backup_type=manifest.backup_type,
                    status="unknown",
                    statistics=manifest.statistics,
                ))
            except (BackupArchiveError, ValueError, OSError):
                continue
        return items

    async def get_workspace_info(self) -> WorkspaceInfo:
        metadata = self._workspace_metadata()
        storage_files = [item for directory in STORAGE_ALLOWLIST for item in (settings.storage_path / directory).rglob("*") if item.is_file()]
        backups = await self.list_backups()
        policy_service = WorkspaceSettingsService(self.db)
        policy = await policy_service.get_backup_policy(DEFAULT_USER_ID)
        successful = [item for item in backups if item.backup_type in {"manual", "scheduled"}]
        last_successful = successful[0].created_at if successful else None
        backup_writable = self.backup_path.is_dir() and os.access(self.backup_path, os.W_OK)
        health = policy_service.build_health(policy, last_successful, backup_writable)
        return WorkspaceInfo(
            workspace_id=uuid.UUID(str(metadata["workspace_id"])),
            name=str(metadata.get("name", "My Research Workspace")),
            workspace_path=str(self.workspace_path),
            backup_path=str(self.backup_path),
            database_bytes=_directory_size(self.workspace_path / "database"),
            storage_bytes=sum(item.stat().st_size for item in storage_files),
            storage_file_count=len(storage_files),
            statistics=await self._statistics(),
            last_backup_at=backups[0].created_at if backups else None,
            last_successful_backup_at=last_successful,
            last_verified_at=policy.last_verified_at,
            backup_health=health,
        )

    async def delete_backup(self, backup_id: uuid.UUID) -> None:
        try:
            async with workspace_lock.exclusive():
                self._find_backup(backup_id).unlink()
        except WorkspaceBusyError as exc:
            raise BackupError(str(exc)) from exc

    async def restore_backup(self, backup_id: uuid.UUID) -> RestoreResult:
        try:
            async with workspace_lock.exclusive():
                source = self._find_backup(backup_id)
                verification = await self._verify_path(source)
                if not verification.valid or not verification.manifest:
                    raise BackupError("备份未通过校验，不能恢复: " + "; ".join(verification.errors))
                emergency = await self._create_backup_unlocked("emergency")
                restore_root = Path(tempfile.mkdtemp(prefix="restore-", dir=self.workspace_path))
                staged_storage = self.workspace_path / f"storage.restore-{uuid.uuid4().hex}"
                previous_storage = self.workspace_path / f"storage.pre-restore-{uuid.uuid4().hex}"
                swapped = False
                try:
                    await asyncio.to_thread(extract_archive_safely, source, restore_root)
                    extracted_manifest = BackupManifest.model_validate(json.loads((restore_root / MANIFEST_NAME).read_text(encoding="utf-8")))
                    if extracted_manifest.backup_id != backup_id:
                        raise BackupError("恢复归档身份校验失败")
                    dump_path = restore_root / DATABASE_DUMP_PATH
                    await self._validate_dump(dump_path)
                    await asyncio.to_thread(_copy_storage, restore_root / "storage", staged_storage)
                    archive_checksums = json.loads((restore_root / CHECKSUMS_NAME).read_text(encoding="utf-8"))
                    for name, expected in archive_checksums["files"].items():
                        if name.startswith("storage/"):
                            candidate = restore_root / name
                            staged_candidate = staged_storage / Path(name).relative_to("storage")
                            if (
                                not candidate.is_file()
                                or not staged_candidate.is_file()
                                or sha256_file(candidate) != expected
                                or sha256_file(staged_candidate) != expected
                            ):
                                raise BackupError(f"恢复前文件校验失败: {name}")
                    await self._restore_database(dump_path)
                    storage_root = settings.storage_path
                    os.replace(storage_root, previous_storage)
                    os.replace(staged_storage, storage_root)
                    swapped = True
                    async with AsyncSession(engine, expire_on_commit=False) as validation_db:
                        validation_service = BackupService(validation_db)
                        restored_stats = await validation_service._statistics()
                        if restored_stats != extracted_manifest.statistics:
                            raise BackupError("恢复后的数据库统计与备份 manifest 不一致")
                        document_paths = (await validation_db.execute(text("SELECT file_path FROM documents"))).scalars().all()
                    missing_paths = [path for path in document_paths if not (settings.storage_path / path).is_file()]
                    if missing_paths:
                        raise BackupError(f"恢复后有 {len(missing_paths)} 个 Document 文件缺失")
                    # The swapped-out directory is only needed until all restore checks pass.
                    shutil.rmtree(previous_storage, ignore_errors=True)
                    return RestoreResult(restored_backup_id=backup_id, emergency_backup_id=emergency.backup_id, statistics=restored_stats)
                except Exception as exc:
                    emergency_path = self._find_backup(emergency.backup_id)
                    try:
                        with tempfile.TemporaryDirectory(prefix="rollback-") as rollback_dir:
                            rollback_root = Path(rollback_dir)
                            await asyncio.to_thread(extract_archive_safely, emergency_path, rollback_root)
                            await self._restore_database(rollback_root / DATABASE_DUMP_PATH)
                            if swapped:
                                failed_storage = self.workspace_path / f"storage.failed-{uuid.uuid4().hex}"
                                os.replace(settings.storage_path, failed_storage)
                                os.replace(previous_storage, settings.storage_path)
                    except Exception as rollback_error:
                        raise BackupError(f"恢复失败且自动回退失败: {rollback_error}") from exc
                    raise BackupError(f"恢复失败，已自动回退到恢复前状态: {exc}") from exc
                finally:
                    shutil.rmtree(restore_root, ignore_errors=True)
                    shutil.rmtree(staged_storage, ignore_errors=True)
        except WorkspaceBusyError as exc:
            raise BackupError(str(exc)) from exc


def get_backup_service(db: AsyncSession = Depends(get_db)) -> BackupService:
    return BackupService(db)
