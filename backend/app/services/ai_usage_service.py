import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIRequestRecord
from app.schemas.ai_infrastructure import AIRequestPage, AIRequestResponse, AIUsageSummary


class AIUsageService:
    def __init__(self, db: AsyncSession): self.db = db

    @staticmethod
    def _filters(user_id: uuid.UUID, start: datetime | None, end: datetime | None,
                 feature: str | None, provider_id: uuid.UUID | None, model_id: uuid.UUID | None,
                 paper_id: uuid.UUID | None, status: str | None) -> list:
        result = [AIRequestRecord.user_id == user_id]
        if start: result.append(AIRequestRecord.created_at >= start)
        if end: result.append(AIRequestRecord.created_at < end)
        if feature: result.append(AIRequestRecord.feature == feature)
        if provider_id: result.append(AIRequestRecord.provider_id == provider_id)
        if model_id: result.append(AIRequestRecord.model_id == model_id)
        if paper_id: result.append(AIRequestRecord.paper_id == paper_id)
        if status: result.append(AIRequestRecord.status == status)
        return result

    async def summary(self, user_id: uuid.UUID, **params) -> AIUsageSummary:
        filters = self._filters(user_id, **params)
        row = (await self.db.execute(select(
            func.count(AIRequestRecord.id),
            func.count(AIRequestRecord.id).filter(AIRequestRecord.status == "completed"),
            func.coalesce(func.sum(AIRequestRecord.input_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.cached_input_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.output_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.total_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.actual_cost).filter(AIRequestRecord.actual_cost.is_not(None)), 0),
            func.count(AIRequestRecord.id).filter(AIRequestRecord.cost_status == "unknown"),
            func.min(AIRequestRecord.currency).filter(AIRequestRecord.actual_cost.is_not(None)),
            func.count(func.distinct(AIRequestRecord.currency)).filter(AIRequestRecord.actual_cost.is_not(None)),
        ).where(*filters))).one()
        # Never combine different currencies into a misleading total.
        cost = Decimal(row[6]) if row[9] <= 1 else Decimal(0)
        return AIUsageSummary(request_count=row[0], success_count=row[1], input_tokens=row[2],
            cached_input_tokens=row[3], output_tokens=row[4], total_tokens=row[5],
            calculated_cost=cost, unknown_cost_requests=row[7], currency=row[8] if row[9] <= 1 else None)

    async def requests(self, user_id: uuid.UUID, page: int, page_size: int, **params) -> AIRequestPage:
        filters = self._filters(user_id, **params)
        total = await self.db.scalar(select(func.count()).select_from(AIRequestRecord).where(*filters)) or 0
        rows = (await self.db.scalars(select(AIRequestRecord).where(*filters)
            .order_by(AIRequestRecord.created_at.desc(), AIRequestRecord.id.desc())
            .offset((page - 1) * page_size).limit(page_size))).all()
        return AIRequestPage(items=[AIRequestResponse.model_validate(row) for row in rows], total=total, page=page, page_size=page_size)

    async def grouped(self, user_id: uuid.UUID, dimension: str, **params) -> list[dict]:
        filters = self._filters(user_id, **params)
        column = {"feature": AIRequestRecord.feature, "model": AIRequestRecord.model_id,
                  "paper": AIRequestRecord.paper_id}.get(dimension)
        if column is None: raise ValueError("Unsupported usage dimension")
        rows = (await self.db.execute(select(column, func.count(), func.coalesce(func.sum(AIRequestRecord.total_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.actual_cost), 0),
            func.count().filter(AIRequestRecord.cost_status == "unknown"))
            .where(*filters).group_by(column).order_by(func.count().desc()))).all()
        return [{"key": str(row[0]) if row[0] is not None else None, "requests": row[1], "tokens": row[2],
                 "cost": str(row[3]), "unknown_cost_requests": row[4]} for row in rows]

    async def timeseries(self, user_id: uuid.UUID, **params) -> list[dict]:
        filters = self._filters(user_id, **params)
        day = func.date_trunc("day", AIRequestRecord.created_at)
        rows = (await self.db.execute(select(day, func.count(), func.coalesce(func.sum(AIRequestRecord.total_tokens), 0),
            func.coalesce(func.sum(AIRequestRecord.actual_cost), 0),
            func.count().filter(AIRequestRecord.cost_status == "unknown"))
            .where(*filters).group_by(day).order_by(day))).all()
        return [{"date": row[0], "requests": row[1], "tokens": row[2], "cost": str(row[3]), "unknown_cost_requests": row[4]} for row in rows]
