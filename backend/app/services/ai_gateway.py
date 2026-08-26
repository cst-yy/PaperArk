"""Unified metered generation gateway with historical pricing and budget reservation."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AIBudgetPolicy, AIBudgetReservation, AIModelPricing, AIRequestRecord
from app.processors.generation import GenerationMessage, GenerationProvider, GenerationResult, OpenAICompatibleGenerationProvider
from app.services.ai_cost import PriceSnapshot, calculate_cost, estimate_tokens
from app.services.ai_provider_service import AIProviderService


class AIBudgetExceededError(RuntimeError):
    pass


class AIGateway:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, *, user_id: uuid.UUID, feature: str, operation: str,
                       messages: list[GenerationMessage], max_tokens: int,
                       temperature: float = 0.1, paper_id: uuid.UUID | None = None,
                       model_id: uuid.UUID | None = None, context_type: str | None = None,
                       context_id: uuid.UUID | None = None,
                       fallback_provider: GenerationProvider | None = None) -> tuple[GenerationResult, AIRequestRecord]:
        provider_row = model_row = None
        if model_id:
            provider_row, model_row, adapter = await AIProviderService(self.db).adapter(user_id, model_id)
            await self.db.refresh(provider_row, with_for_update=True)
            active = await self.db.scalar(select(func.count()).select_from(AIRequestRecord).where(
                AIRequestRecord.provider_id == provider_row.id, AIRequestRecord.status == "reserved")) or 0
            if active >= provider_row.max_concurrency:
                raise AIBudgetExceededError("当前 Provider 已达到最大并发请求数")
        else:
            adapter = fallback_provider or OpenAICompatibleGenerationProvider()
        prompt_text = "\n".join(message["content"] for message in messages)
        estimated_input = estimate_tokens(prompt_text)
        price = await self._price(model_id)
        estimated_cost = calculate_cost(estimated_input, 0, max_tokens, price) if price else None
        record = AIRequestRecord(
            user_id=user_id, provider_id=provider_row.id if provider_row else None,
            model_id=model_row.id if model_row else None, paper_id=paper_id,
            feature=feature, operation=operation, status="reserved",
            input_tokens=estimated_input, output_tokens=max_tokens,
            total_tokens=estimated_input + max_tokens, token_source="estimate",
            estimated_cost=estimated_cost, currency=price.currency if price else None,
            cost_status="estimated" if estimated_cost is not None else "unknown",
            price_snapshot=price.as_dict() if price else None,
            context_type=context_type, context_id=context_id,
        )
        self.db.add(record)
        await self.db.flush()
        await self._reserve(user_id, record, feature, paper_id, provider_row.id if provider_row else None,
                            model_row.id if model_row else None, estimated_input + max_tokens, estimated_cost)
        await self.db.commit()  # release policy row locks before network I/O

        started = time.monotonic()
        try:
            result = await adapter.generate(messages, temperature, max_tokens)
        except Exception as exc:
            record = await self.db.get(AIRequestRecord, record.id)
            assert record is not None
            record.status = "failed"
            record.duration_ms = int((time.monotonic() - started) * 1000)
            record.completed_at = datetime.now(timezone.utc)
            record.error_type = type(exc).__name__
            record.safe_error = "AI Provider 请求失败"
            record.cost_status = "unknown"
            await self._finish_reservations(record.id, consumed=False)
            await self.db.commit()
            raise

        actual_input = result.prompt_tokens if result.prompt_tokens is not None else estimated_input
        actual_output = result.completion_tokens if result.completion_tokens is not None else estimate_tokens(result.text)
        cached = result.cached_prompt_tokens or 0
        actual_cost = calculate_cost(actual_input, cached, actual_output, price) if price else None
        record = await self.db.get(AIRequestRecord, record.id)
        assert record is not None
        record.status = "completed"
        record.provider_request_id = result.provider_request_id
        record.input_tokens = actual_input
        record.cached_input_tokens = cached
        record.output_tokens = actual_output
        record.total_tokens = actual_input + actual_output
        record.token_source = "provider" if result.prompt_tokens is not None and result.completion_tokens is not None else "estimate"
        record.actual_cost = actual_cost
        record.cost_status = "calculated" if actual_cost is not None else "unknown"
        record.duration_ms = int((time.monotonic() - started) * 1000)
        record.completed_at = datetime.now(timezone.utc)
        await self._finish_reservations(record.id, consumed=True)
        await self.db.commit()
        return result, record

    async def _price(self, model_id: uuid.UUID | None) -> PriceSnapshot | None:
        if not model_id:
            return None
        row = await self.db.scalar(select(AIModelPricing).where(
            AIModelPricing.model_id == model_id, AIModelPricing.effective_to.is_(None)
        ).order_by(AIModelPricing.effective_from.desc()))
        return PriceSnapshot(row.currency, row.input_per_million, row.cached_input_per_million, row.output_per_million) if row else None

    async def _reserve(self, user_id: uuid.UUID, record: AIRequestRecord, feature: str,
                       paper_id: uuid.UUID | None, provider_id: uuid.UUID | None,
                       model_id: uuid.UUID | None, tokens: int, cost: Decimal | None) -> None:
        scopes = [("global", None), ("feature", feature)]
        if paper_id: scopes.append(("paper", str(paper_id)))
        if provider_id: scopes.append(("provider", str(provider_id)))
        if model_id: scopes.append(("model", str(model_id)))
        clauses = [and_(AIBudgetPolicy.scope_type == kind,
                        AIBudgetPolicy.scope_id.is_(None) if key is None else AIBudgetPolicy.scope_id == key)
                   for kind, key in scopes]
        policies = list((await self.db.scalars(select(AIBudgetPolicy).where(
            AIBudgetPolicy.user_id == user_id, AIBudgetPolicy.enabled.is_(True), or_(*clauses)
        ).with_for_update())).all())
        now = datetime.now(timezone.utc)
        for policy in policies:
            start = self._period_start(policy.period_type, now)
            request_filter = [AIRequestRecord.user_id == user_id, AIRequestRecord.status == "completed"]
            if start: request_filter.append(AIRequestRecord.created_at >= start)
            used_tokens, used_cost = (await self.db.execute(select(
                func.coalesce(func.sum(AIRequestRecord.total_tokens), 0),
                func.coalesce(func.sum(AIRequestRecord.actual_cost), 0),
            ).where(*request_filter))).one()
            active_tokens, active_cost = (await self.db.execute(select(
                func.coalesce(func.sum(AIBudgetReservation.reserved_tokens), 0),
                func.coalesce(func.sum(AIBudgetReservation.reserved_cost), 0),
            ).where(AIBudgetReservation.budget_policy_id == policy.id,
                    AIBudgetReservation.status == "active", AIBudgetReservation.expires_at > now))).one()
            if policy.token_limit is not None and int(used_tokens) + int(active_tokens) + tokens > policy.token_limit and policy.hard_limit:
                raise AIBudgetExceededError("AI Token 预算不足")
            if policy.cost_limit is not None:
                if cost is None and policy.hard_limit:
                    raise AIBudgetExceededError("当前模型缺少价格，无法在费用硬限额下执行")
                if cost is not None and Decimal(used_cost) + Decimal(active_cost) + cost > policy.cost_limit and policy.hard_limit:
                    raise AIBudgetExceededError("AI 费用预算不足")
            self.db.add(AIBudgetReservation(user_id=user_id, request_id=record.id,
                budget_policy_id=policy.id, reserved_tokens=tokens, reserved_cost=cost,
                expires_at=now + timedelta(minutes=15)))

    async def _finish_reservations(self, request_id: uuid.UUID, *, consumed: bool) -> None:
        rows = (await self.db.scalars(select(AIBudgetReservation).where(
            AIBudgetReservation.request_id == request_id, AIBudgetReservation.status == "active"
        ))).all()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = "consumed" if consumed else "released"
            row.released_at = now

    @staticmethod
    def _period_start(period: str, now: datetime) -> datetime | None:
        if period == "per_request": return now
        if period == "daily": return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "weekly":
            day = now - timedelta(days=now.weekday())
            return day.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "monthly": return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None
