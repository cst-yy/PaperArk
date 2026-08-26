import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    GenerationProviderError,
    PaperNotFoundError,
    RAGContextError,
    SemanticRetrievalError,
    StructuredGenerationError,
    AIAnalysisNotFoundError,
    InvalidAIAnalysisError,
    InvalidNoteError,
    NoteNotFoundError,
    RevisionConflictError,
)
from app.processors.generation import GenerationProvider, OpenAICompatibleGenerationProvider
from app.schemas.ai import PaperQARequest, PaperQAResponse, TranslationRequest, TranslationResult
from app.schemas.deep_reading import (
    AIAnalysisApplyRequest, AIAnalysisApplyResponse, AIAnalysisDetail,
    DeepReadingDraft, DeepReadingRequest,
)
from app.services.ai_service import AIService
from app.services.deep_reading_service import DeepReadingService
from app.services.ai_analysis_service import AIAnalysisService
from app.services.ai_gateway import AIBudgetExceededError

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
    except AIBudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except (GenerationProviderError, SemanticRetrievalError) as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc


@router.post("/translate", response_model=TranslationResult)
async def translate_selection(
    request: TranslationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    provider: GenerationProvider = Depends(get_generation_provider),
):
    try:
        return await AIService(db, provider).translate_user_selection(user_id, request)
    except AIBudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
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
    except AIBudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except (GenerationProviderError, SemanticRetrievalError, StructuredGenerationError) as exc:
        raise HTTPException(status_code=503, detail="AI structured analysis is temporarily unavailable") from exc


@router.get("/analyses/{analysis_id}", response_model=AIAnalysisDetail)
async def get_analysis(
    analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await AIAnalysisService(db).get_detail(user_id, analysis_id)
    except AIAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response:
    try:
        await AIAnalysisService(db).delete(user_id, analysis_id)
    except AIAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/analyses/{analysis_id}/apply", response_model=AIAnalysisApplyResponse)
async def apply_analysis(
    analysis_id: uuid.UUID, request: AIAnalysisApplyRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await AIAnalysisService(db).apply(user_id, analysis_id, request)
    except AIAnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except RevisionConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except (InvalidAIAnalysisError, InvalidNoteError) as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
