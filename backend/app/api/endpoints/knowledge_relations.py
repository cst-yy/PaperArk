import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import (
    DuplicatePaperRelationError, InvalidPaperRelationError, PaperRelationNotFoundError,
)
from app.processors.generation import OpenAICompatibleGenerationProvider
from app.schemas.knowledge_relation import (
    KnowledgeRelationResponse, RelationEvidenceReplacement, RelationSuggestionResponse,
)
from app.services.knowledge_relation_service import KnowledgeRelationService
from app.services.relation_suggestion_service import RelationSuggestionService

router = APIRouter()


def _error(error: Exception) -> HTTPException:
    code = 404 if isinstance(error, PaperRelationNotFoundError) else 409 if isinstance(error, DuplicatePaperRelationError) else 422
    return HTTPException(status_code=code, detail=getattr(error, "message", str(error)))


@router.get("/{relation_id}", response_model=KnowledgeRelationResponse)
async def get_relation(relation_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await KnowledgeRelationService(db).get(user_id, relation_id)
    except PaperRelationNotFoundError as error: raise _error(error) from error


@router.put("/{relation_id}/evidence", response_model=KnowledgeRelationResponse)
async def replace_relation_evidence(relation_id: uuid.UUID, data: RelationEvidenceReplacement,
                                    db: AsyncSession = Depends(get_db),
                                    user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await KnowledgeRelationService(db).replace_evidence(user_id, relation_id, data)
    except (PaperRelationNotFoundError, InvalidPaperRelationError) as error: raise _error(error) from error


@router.post("/suggestions/{suggestion_id}/accept", response_model=RelationSuggestionResponse)
async def accept_suggestion(suggestion_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                            user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await RelationSuggestionService(db, OpenAICompatibleGenerationProvider()).accept(user_id, suggestion_id)
    except (InvalidPaperRelationError, DuplicatePaperRelationError) as error: raise _error(error) from error


@router.post("/suggestions/{suggestion_id}/reject", response_model=RelationSuggestionResponse)
async def reject_suggestion(suggestion_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                            user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await RelationSuggestionService(db, OpenAICompatibleGenerationProvider()).reject(user_id, suggestion_id)
    except InvalidPaperRelationError as error: raise _error(error) from error
