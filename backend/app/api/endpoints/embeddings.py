import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.processors.embedding import OpenAICompatibleEmbeddingProvider
from app.services.embedding_service import EmbeddingLifecycleService

router = APIRouter()


class RebuildRequest(BaseModel):
    scope: Literal["all"] = "all"


@router.post("/rebuild")
async def rebuild_embeddings(_: RebuildRequest, db: AsyncSession = Depends(get_db),
                             user_id: uuid.UUID = Depends(get_current_user_id)):
    provider = OpenAICompatibleEmbeddingProvider()
    result = await EmbeddingLifecycleService(db, provider).rebuild(user_id)
    return {"processed": result.processed, "skipped": result.skipped, "failed": result.failed,
            "model": provider.model_name, "dimension": provider.dimension}


@router.get("/status")
async def embedding_status(db: AsyncSession = Depends(get_db),
                           user_id: uuid.UUID = Depends(get_current_user_id)):
    provider = OpenAICompatibleEmbeddingProvider()
    counts = await EmbeddingLifecycleService(db, provider).status(user_id)
    return {"model": provider.model_name, "dimension": provider.dimension, "entities": counts}
