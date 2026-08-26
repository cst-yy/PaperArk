import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.models import AIBudgetPolicy, AIRequestRecord
from app.schemas.ai_infrastructure import *
from app.services.ai_provider_service import AIProviderService
from app.services.ai_usage_service import AIUsageService

router = APIRouter()


@router.get("/providers", response_model=list[AIProviderResponse])
async def providers(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await AIProviderService(db).list(user_id)


@router.post("/providers", response_model=AIProviderResponse, status_code=201)
async def create_provider(data: AIProviderCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIProviderService(db).create(user_id, data)
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc


@router.patch("/providers/{provider_id}", response_model=AIProviderResponse)
async def update_provider(provider_id: uuid.UUID, data: AIProviderUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIProviderService(db).update(user_id, provider_id, data)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: await AIProviderService(db).delete(user_id, provider_id)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIProviderService(db).test(user_id, provider_id)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc


@router.get("/models", response_model=list[AIModelResponse])
async def models(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await AIProviderService(db).list_models(user_id)


@router.post("/models", response_model=AIModelResponse, status_code=201)
async def create_model(data: AIModelCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIProviderService(db).create_model(user_id, data)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc


@router.post("/models/{model_id}/pricing", response_model=AIModelPricingResponse, status_code=201)
async def add_pricing(model_id: uuid.UUID, data: AIModelPricingCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIProviderService(db).add_pricing(user_id, model_id, data)
    except LookupError as exc: raise HTTPException(404, detail=str(exc)) from exc


@router.get("/budgets", response_model=list[AIBudgetResponse])
async def budgets(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return list((await db.scalars(select(AIBudgetPolicy).where(AIBudgetPolicy.user_id == user_id).order_by(AIBudgetPolicy.created_at))).all())


@router.post("/budgets", response_model=AIBudgetResponse, status_code=201)
async def create_budget(data: AIBudgetCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = AIBudgetPolicy(user_id=user_id, **data.model_dump()); db.add(row); await db.flush(); return row


@router.patch("/budgets/{budget_id}", response_model=AIBudgetResponse)
async def update_budget(budget_id: uuid.UUID, data: AIBudgetCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(select(AIBudgetPolicy).where(AIBudgetPolicy.id == budget_id, AIBudgetPolicy.user_id == user_id))
    if not row: raise HTTPException(404, detail="AI budget not found")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    await db.flush(); return row


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(budget_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(select(AIBudgetPolicy).where(AIBudgetPolicy.id == budget_id, AIBudgetPolicy.user_id == user_id))
    if not row: raise HTTPException(404, detail="AI budget not found")
    await db.delete(row); return Response(status_code=204)


def usage_filters(start: datetime | None = None, end: datetime | None = None, feature: str | None = None,
                  provider_id: uuid.UUID | None = None, model_id: uuid.UUID | None = None,
                  paper_id: uuid.UUID | None = None, status: str | None = None):
    return dict(start=start, end=end, feature=feature, provider_id=provider_id, model_id=model_id, paper_id=paper_id, status=status)


@router.get("/usage/summary", response_model=AIUsageSummary)
async def usage_summary(start: datetime | None = None, end: datetime | None = None, feature: str | None = None,
                        provider_id: uuid.UUID | None = None, model_id: uuid.UUID | None = None,
                        paper_id: uuid.UUID | None = None, status: str | None = None,
                        db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await AIUsageService(db).summary(user_id, **usage_filters(start,end,feature,provider_id,model_id,paper_id,status))


@router.get("/usage/requests", response_model=AIRequestPage)
async def usage_requests(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         start: datetime | None = None, end: datetime | None = None, feature: str | None = None,
                         provider_id: uuid.UUID | None = None, model_id: uuid.UUID | None = None,
                         paper_id: uuid.UUID | None = None, status: str | None = None,
                         db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await AIUsageService(db).requests(user_id, page, page_size, **usage_filters(start,end,feature,provider_id,model_id,paper_id,status))


@router.get("/usage/requests/{request_id}", response_model=AIRequestResponse)
async def usage_request(request_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(select(AIRequestRecord).where(AIRequestRecord.id == request_id, AIRequestRecord.user_id == user_id))
    if not row: raise HTTPException(404, detail="AI request not found")
    return row


@router.get("/usage/timeseries")
async def usage_timeseries(start: datetime | None = None, end: datetime | None = None, feature: str | None = None,
                           provider_id: uuid.UUID | None = None, model_id: uuid.UUID | None = None,
                           paper_id: uuid.UUID | None = None, status: str | None = None,
                           db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return await AIUsageService(db).timeseries(user_id, **usage_filters(start,end,feature,provider_id,model_id,paper_id,status))


@router.get("/usage/by-{dimension}")
async def usage_grouped(dimension: str, start: datetime | None = None, end: datetime | None = None, feature: str | None = None,
                        provider_id: uuid.UUID | None = None, model_id: uuid.UUID | None = None,
                        paper_id: uuid.UUID | None = None, status: str | None = None,
                        db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await AIUsageService(db).grouped(user_id, dimension, **usage_filters(start,end,feature,provider_id,model_id,paper_id,status))
    except ValueError as exc: raise HTTPException(404, detail=str(exc)) from exc
