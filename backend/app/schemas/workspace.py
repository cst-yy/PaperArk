from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


BackupFrequency = Literal["daily", "weekly"]
BackupHealthStatus = Literal["healthy", "warning", "critical"]


class BackupPolicy(BaseModel):
    enabled: bool = False
    frequency: BackupFrequency = "daily"
    retention: int = Field(default=7, ge=1, le=100)
    last_scheduled_backup_at: datetime | None = None
    last_backup_status: Literal["success", "failed", "never"] = "never"
    last_backup_error: str | None = None
    last_verified_at: datetime | None = None
    last_verified_backup_id: str | None = None
    last_verification_status: Literal["valid", "invalid", "never"] = "never"


class BackupPolicyUpdate(BaseModel):
    enabled: bool | None = None
    frequency: BackupFrequency | None = None
    retention: int | None = Field(default=None, ge=1, le=100)


class BackupHealth(BaseModel):
    status: BackupHealthStatus
    label: str
    reason: str
    last_successful_backup_at: datetime | None = None
    last_verified_at: datetime | None = None
    backup_due: bool
    policy: BackupPolicy


class WorkspaceSettingsResponse(BaseModel):
    policy: BackupPolicy
    health: BackupHealth
