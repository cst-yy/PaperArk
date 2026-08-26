from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "paperark",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.translation_tasks"],
)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"],
                       task_acks_late=True, worker_prefetch_multiplier=1,
                       broker_connection_retry_on_startup=True,
                       task_routes={"app.tasks.translation_tasks.*": {"queue": "ai"}})
