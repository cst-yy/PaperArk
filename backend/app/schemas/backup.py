from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.workspace import BackupHealth


class BackupDatabaseInfo(BaseModel):
    engine: Literal["postgresql"] = "postgresql"
    major_version: int
    schema_revision: str
    dump_format: Literal["custom"] = "custom"


class BackupStatistics(BaseModel):
    papers: int
    documents: int
    annotations: int
    notes: int
    pdf_files: int


class BackupStorageInfo(BaseModel):
    file_count: int
    total_bytes: int


class BackupManifest(BaseModel):
    format: Literal["AIResearchWorkspace"] = "AIResearchWorkspace"
    format_version: int = Field(ge=1)
    backup_id: UUID
    workspace_id: UUID
    created_at: datetime
    app_version: str
    backup_type: Literal["manual", "emergency", "scheduled"] = "manual"
    database: BackupDatabaseInfo
    statistics: BackupStatistics
    storage: BackupStorageInfo


class BackupItem(BaseModel):
    backup_id: UUID
    filename: str
    created_at: datetime
    size_bytes: int
    format_version: int
    schema_revision: str
    backup_type: str
    status: Literal["unknown", "verified", "invalid", "unsupported"] = "unknown"
    statistics: BackupStatistics


class BackupVerificationResult(BaseModel):
    valid: bool
    status: Literal["valid", "invalid", "unsupported", "corrupted"]
    errors: list[str] = []
    warnings: list[str] = []
    manifest: BackupManifest | None = None


class WorkspaceInfo(BaseModel):
    workspace_id: UUID
    name: str
    workspace_path: str
    backup_path: str
    database_bytes: int
    storage_bytes: int
    storage_file_count: int
    statistics: BackupStatistics
    last_backup_at: datetime | None = None
    last_successful_backup_at: datetime | None = None
    last_verified_at: datetime | None = None
    backup_health: BackupHealth | None = None


class RestoreResult(BaseModel):
    restored_backup_id: UUID
    emergency_backup_id: UUID
    statistics: BackupStatistics
