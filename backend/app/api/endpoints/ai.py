import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    GenerationProviderError,
    PaperNotFoundError,
    RAGContextError,
    SemanticRetrievalError,
    StructuredGenerationError,
)
from app.processors.generation import GenerationProvider, OpenAICompatibleGenerationProvider
from app.schemas.ai import PaperQARequest, PaperQAResponse, TranslationRequest, TranslationResult
from app.schemas.deep_reading import DeepReadingDraft, DeepReadingRequest
from app.services.ai_service import AIService
from app.services.deep_reading_service import DeepReadingService

router = APIRouter()


def get_generation_provider() -> GenerationProvider:
    return OpenAICompatibleGenerationProvider()


@router.post("/qa", response_model=PaperQAResponse)
async def answer_paper_question(
    request: PaperQARequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    provider: GenerationProvider = Depends(get_generation_provider),
):
    try:
        return await AIService(db, provider).answer_paper_question(user_id, request)
    except (PaperNotFoundError, RAGContextError) as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except (GenerationProviderError, SemanticRetrievalError) as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc


@router.post("/translate", response_model=TranslationResult)
async def translate_selection(
    request: TranslationRequest,
    db: AsyncSession = Depends(get_db),
    provider: GenerationProvider = Depends(get_generation_provider),
):
    try:
        return await AIService(db, provider).translate_selection(request)
    except GenerationProviderError as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc


@router.post("/deep-reading", response_model=DeepReadingDraft)
async def generate_deep_reading(
    request: DeepReadingRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    provider: GenerationProvider = Depends(get_generation_provider),
):
    try:
        return await DeepReadingService(db, provider).generate(user_id, request)
    except RAGContextError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except (GenerationProviderError, SemanticRetrievalError, StructuredGenerationError) as exc:
        raise HTTPException(status_code=503, detail="AI structured analysis is temporarily unavailable") from exc
