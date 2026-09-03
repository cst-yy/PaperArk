import asyncio
import uuid
from typing import Any, Coroutine

from app.tasks.celery_app import celery_app
from app.services.translation_service import TranslationService


# Celery executes tasks in long-lived worker processes while SQLAlchemy's
# asyncpg pool keeps connections bound to the event loop that first used them.
# Creating a fresh loop with asyncio.run() for every task leaves pooled
# connections attached to a closed/different loop on the next translation.
_worker_loop: asyncio.AbstractEventLoop | None = None


def _run_on_worker_loop(coroutine: Coroutine[Any, Any, None]) -> None:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coroutine)


@celery_app.task(name="app.tasks.translation_tasks.run_translation", autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def run_translation(user_id: str, job_id: str) -> None:
    _run_on_worker_loop(TranslationService.run_background(uuid.UUID(user_id), uuid.UUID(job_id)))


def enqueue_translation(user_id: uuid.UUID, job_id: uuid.UUID) -> None:
    run_translation.delay(str(user_id), str(job_id))
