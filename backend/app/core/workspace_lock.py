import asyncio
from contextlib import asynccontextmanager


class WorkspaceBusyError(RuntimeError):
    pass


class WorkspaceLock:
    """Process-local exclusive lock for backup and restore operations."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def is_locked(self) -> bool:
        return self._lock.locked()

    @asynccontextmanager
    async def exclusive(self):
        if self._lock.locked():
            raise WorkspaceBusyError("工作区正在执行备份或恢复操作")
        await self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()


workspace_lock = WorkspaceLock()
