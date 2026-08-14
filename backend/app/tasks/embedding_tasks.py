"""Explicit embedding refresh entry point; never runs during application startup."""
import uuid

from app.core.database import async_session_factory
from app.processors.embedding import OpenAICompatibleEmbeddingProvider
from app.services.embedding_service import EmbeddingLifecycleService


async def rebuild_user_embeddings(user_id: uuid.UUID) -> dict[str, int]:
    async with async_session_factory() as db:
        result = await EmbeddingLifecycleService(db, OpenAICompatibleEmbeddingProvider()).rebuild(user_id)
        return {"processed": result.processed, "skipped": result.skipped, "failed": result.failed}
