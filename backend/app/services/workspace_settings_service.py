import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Setting
from app.schemas.workspace import BackupHealth, BackupPolicy, BackupPolicyUpdate

_BACKUP_POLICY_KEY = "workspace.backup_policy"


class WorkspaceSettingsService:
    """Persists workspace-level protection policy in the existing Setting table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_backup_policy(self, user_id: uuid.UUID) -> BackupPolicy:
        setting = await self.db.scalar(
            select(Setting).where(Setting.user_id == user_id, Setting.key == _BACKUP_POLICY_KEY)
        )
        if not setting:
            return BackupPolicy()
        try:
            return BackupPolicy.model_validate_json(setting.value)
        except ValueError:
            return BackupPolicy()

    async def update_backup_policy(self, user_id: uuid.UUID, update: BackupPolicyUpdate) -> BackupPolicy:
        policy = await self.get_backup_policy(user_id)
        return await self._save_policy(user_id, policy.model_copy(update=update.model_dump(exclude_unset=True)))

    async def record_scheduled_success(self, user_id: uuid.UUID, when: datetime) -> BackupPolicy:
        return await self._update_runtime(
            user_id, last_scheduled_backup_at=when, last_backup_status="success", last_backup_error=None
        )

    async def record_scheduled_failure(self, user_id: uuid.UUID, error: str) -> BackupPolicy:
        return await self._update_runtime(user_id, last_backup_status="failed", last_backup_error=error[:1000])

    async def record_verification(self, user_id: uuid.UUID, backup_id: uuid.UUID, when: datetime) -> BackupPolicy:
        return await self._update_runtime(
            user_id,
            last_verified_at=when,
            last_verified_backup_id=str(backup_id),
            last_verification_status="valid",
        )

    async def record_invalid_verification(self, user_id: uuid.UUID, backup_id: uuid.UUID) -> BackupPolicy:
        return await self._update_runtime(
            user_id,
            last_verified_backup_id=str(backup_id),
            last_verification_status="invalid",
        )

    async def _update_runtime(self, user_id: uuid.UUID, **values: object) -> BackupPolicy:
        policy = await self.get_backup_policy(user_id)
        return await self._save_policy(user_id, policy.model_copy(update=values))

    async def _save_policy(self, user_id: uuid.UUID, policy: BackupPolicy) -> BackupPolicy:
        setting = await self.db.scalar(
            select(Setting).where(Setting.user_id == user_id, Setting.key == _BACKUP_POLICY_KEY)
        )
        serialized = policy.model_dump_json()
        if setting:
            setting.value = serialized
        else:
            self.db.add(Setting(user_id=user_id, key=_BACKUP_POLICY_KEY, value=serialized))
        await self.db.commit()
        return policy

    @staticmethod
    def due_at(policy: BackupPolicy) -> datetime | None:
        if not policy.enabled:
            return None
        if not policy.last_scheduled_backup_at:
            return datetime.min.replace(tzinfo=UTC)
        return policy.last_scheduled_backup_at + timedelta(days=1 if policy.frequency == "daily" else 7)

    @classmethod
    def is_due(cls, policy: BackupPolicy, now: datetime | None = None) -> bool:
        due_at = cls.due_at(policy)
        return bool(due_at and (now or datetime.now(UTC)) >= due_at)

    @classmethod
    def build_health(
        cls,
        policy: BackupPolicy,
        last_successful_backup_at: datetime | None,
        backup_path_writable: bool,
        now: datetime | None = None,
    ) -> BackupHealth:
        now = now or datetime.now(UTC)
        interval = timedelta(days=1 if policy.frequency == "daily" else 7)
        due = bool(policy.enabled and (not last_successful_backup_at or last_successful_backup_at + interval <= now))
        if not backup_path_writable:
            return BackupHealth(status="critical", label="\u4e25\u91cd", reason="\u5907\u4efd\u76ee\u5f55\u4e0d\u53ef\u5199\uff0c\u65e0\u6cd5\u521b\u5efa\u6216\u9a8c\u8bc1\u5907\u4efd\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=policy.last_verified_at, backup_due=due, policy=policy)
        if policy.last_backup_status == "failed":
            return BackupHealth(status="warning", label="\u8b66\u544a", reason=policy.last_backup_error or "\u6700\u8fd1\u4e00\u6b21\u81ea\u52a8\u5907\u4efd\u5931\u8d25\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=policy.last_verified_at, backup_due=due, policy=policy)
        if not last_successful_backup_at:
            return BackupHealth(status="warning", label="\u8b66\u544a", reason="\u81ea\u52a8\u5907\u4efd\u5c1a\u672a\u542f\u7528\uff0c\u4e14\u5c1a\u672a\u521b\u5efa\u6210\u529f\u5907\u4efd\u3002" if not policy.enabled else "\u5c1a\u672a\u521b\u5efa\u6210\u529f\u5907\u4efd\u3002", last_successful_backup_at=None, last_verified_at=policy.last_verified_at, backup_due=due, policy=policy)
        if due:
            return BackupHealth(status="warning", label="\u8b66\u544a", reason="\u5df2\u8d85\u8fc7\u81ea\u52a8\u5907\u4efd\u7b56\u7565\u89c4\u5b9a\u7684\u5468\u671f\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=policy.last_verified_at, backup_due=True, policy=policy)
        if policy.last_verification_status == "invalid":
            return BackupHealth(status="critical", label="\u4e25\u91cd", reason="\u6700\u8fd1\u4e00\u6b21\u5907\u4efd\u6821\u9a8c\u5931\u8d25\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=policy.last_verified_at, backup_due=False, policy=policy)
        if not policy.last_verified_at:
            return BackupHealth(status="warning", label="\u8b66\u544a", reason="\u6700\u8fd1\u5907\u4efd\u5c1a\u672a\u5b8c\u6210\u6821\u9a8c\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=None, backup_due=False, policy=policy)
        return BackupHealth(status="healthy", label="\u5065\u5eb7", reason="\u6700\u8fd1\u5907\u4efd\u5df2\u5728\u7b56\u7565\u5468\u671f\u5185\u5b8c\u6210\u4e14\u901a\u8fc7\u6821\u9a8c\u3002", last_successful_backup_at=last_successful_backup_at, last_verified_at=policy.last_verified_at, backup_due=False, policy=policy)
