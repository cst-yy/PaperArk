import pytest

from app.core.workspace_lock import workspace_lock
from app.services.backup_service import BackupError, BackupService


@pytest.mark.asyncio
async def test_delete_backup_rejects_when_workspace_is_locked(session):
    service = BackupService(session)

    async with workspace_lock.exclusive():
        with pytest.raises(BackupError) as exc_info:
            await service.delete_backup(__import__("uuid").uuid4())

    assert "工作区正在执行备份或恢复操作" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_backup_rejects_when_workspace_is_locked(session):
    service = BackupService(session)

    async with workspace_lock.exclusive():
        with pytest.raises(BackupError) as exc_info:
            await service.verify_backup(__import__("uuid").uuid4())

    assert "工作区正在执行备份或恢复操作" in str(exc_info.value)
