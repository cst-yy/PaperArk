import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory, engine, init_db
from app.core.workspace_lock import workspace_lock
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)


async def _run_due_scheduled_backup() -> None:
    """Best-effort scheduled run; failures must never prevent app availability."""
    try:
        async with async_session_factory() as session:
            await BackupService(session).run_scheduled_backup_if_due()
    except Exception:
        logger.exception("Scheduled workspace backup failed; application remains available")


async def _backup_scheduler() -> None:
    """Lightweight in-process scheduler: startup catch-up, then periodic due checks."""
    while True:
        await _run_due_scheduled_backup()
        await asyncio.sleep(15 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Alembic owns schema creation; this only seeds the local user.
    await init_db()
    scheduler_task = asyncio.create_task(_backup_scheduler())
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        # Shutdown: dispose engine
        await engine.dispose()


app = FastAPI(
    title="AI Research Workspace",
    description="Personal paper reading & research platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def workspace_maintenance_guard(request, call_next):
    """Block every external write while an exclusive workspace operation is active."""
    if workspace_lock.is_locked and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"detail": "工作区正在备份或恢复，请稍后重试"})
    return await call_next(request)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
def root():
    return {"msg": "AI Research Workspace 后端服务正常运行"}