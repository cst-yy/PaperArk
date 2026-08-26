import asyncio
import uuid

from app.tasks.celery_app import celery_app
from app.services.translation_service import TranslationService


@celery_app.task(name="app.tasks.translation_tasks.run_translation", autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def run_translation(user_id: str, job_id: str) -> None:
    asyncio.run(TranslationService.run_background(uuid.UUID(user_id), uuid.UUID(job_id)))


def enqueue_translation(user_id: uuid.UUID, job_id: uuid.UUID) -> None:
    run_translation.delay(str(user_id), str(job_id))
