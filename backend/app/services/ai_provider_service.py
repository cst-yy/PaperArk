from __future__ import annotations

import ipaddress
import socket
import uuid
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secret_crypto import decrypt_secret, encrypt_secret
from app.models import AIModel, AIModelPricing, AIProvider
from app.processors.generation import OpenAICompatibleGenerationProvider
from app.schemas.ai_infrastructure import AIModelCreate, AIModelPricingCreate, AIProviderCreate, AIProviderResponse, AIProviderUpdate


class AIProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, user_id: uuid.UUID) -> list[AIProviderResponse]:
        rows = (await self.db.scalars(select(AIProvider).where(AIProvider.user_id == user_id).order_by(AIProvider.created_at))).all()
        return [self._response(row) for row in rows]

    async def create(self, user_id: uuid.UUID, data: AIProviderCreate) -> AIProviderResponse:
        self._validate_url(data.base_url, data.is_local)
        row = AIProvider(user_id=user_id, name=data.name.strip(), base_url=data.base_url.rstrip("/"),
                         encrypted_api_key=encrypt_secret(data.api_key), is_local=data.is_local,
                         timeout_seconds=data.timeout_seconds, max_concurrency=data.max_concurrency,
                         capabilities={"generation": True, "structured_output": True})
        self.db.add(row)
        await self.db.flush()
        return self._response(row)

    async def update(self, user_id: uuid.UUID, provider_id: uuid.UUID, data: AIProviderUpdate) -> AIProviderResponse:
        row = await self._owned(user_id, provider_id)
        values = data.model_dump(exclude_unset=True)
        url = values.get("base_url", row.base_url)
        local = values.get("is_local", row.is_local)
        self._validate_url(url, local)
        if "api_key" in values:
            row.encrypted_api_key = encrypt_secret(values.pop("api_key"))
        for key, value in values.items():
            setattr(row, key, value.rstrip("/") if key == "base_url" else value)
        await self.db.flush()
        return self._response(row)

    async def delete(self, user_id: uuid.UUID, provider_id: uuid.UUID) -> None:
        row = await self._owned(user_id, provider_id)
        await self.db.delete(row)

    async def test(self, user_id: uuid.UUID, provider_id: uuid.UUID) -> dict:
        row = await self._owned(user_id, provider_id)
        try:
            async with httpx.AsyncClient(timeout=min(row.timeout_seconds, 30)) as client:
                response = await client.get(f"{row.base_url}/models", headers={"Authorization": f"Bearer {decrypt_secret(row.encrypted_api_key)}"})
                response.raise_for_status()
            return {"ok": True, "message": "连接成功"}
        except Exception:
            return {"ok": False, "message": "无法连接 Provider，请检查地址、密钥和网络"}

    async def create_model(self, user_id: uuid.UUID, data: AIModelCreate) -> AIModel:
        await self._owned(user_id, data.provider_id)
        row = AIModel(**data.model_dump())
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_models(self, user_id: uuid.UUID) -> list[AIModel]:
        return list((await self.db.scalars(select(AIModel).join(AIProvider).where(AIProvider.user_id == user_id).order_by(AIModel.created_at))).all())

    async def add_pricing(self, user_id: uuid.UUID, model_id: uuid.UUID, data: AIModelPricingCreate) -> AIModelPricing:
        model = await self.db.scalar(select(AIModel).join(AIProvider).where(AIModel.id == model_id, AIProvider.user_id == user_id))
        if not model:
            raise LookupError("AI model not found")
        current = await self.db.scalar(select(AIModelPricing).where(AIModelPricing.model_id == model_id, AIModelPricing.effective_to.is_(None)).order_by(AIModelPricing.effective_from.desc()))
        if current:
            from datetime import datetime, timezone
            current.effective_to = datetime.now(timezone.utc)
        row = AIModelPricing(model_id=model_id, **data.model_dump())
        self.db.add(row)
        await self.db.flush()
        return row

    async def adapter(self, user_id: uuid.UUID, model_id: uuid.UUID) -> tuple[AIProvider, AIModel, OpenAICompatibleGenerationProvider]:
        model = await self.db.scalar(select(AIModel).join(AIProvider).where(AIModel.id == model_id, AIProvider.user_id == user_id, AIProvider.enabled.is_(True), AIModel.enabled.is_(True)))
        if not model:
            raise LookupError("AI model not found or disabled")
        provider = await self.db.get(AIProvider, model.provider_id)
        assert provider is not None
        self._validate_url(provider.base_url, provider.is_local)
        return provider, model, OpenAICompatibleGenerationProvider(base_url=provider.base_url, api_key=decrypt_secret(provider.encrypted_api_key), model_name=model.model_name)

    async def _owned(self, user_id: uuid.UUID, provider_id: uuid.UUID) -> AIProvider:
        row = await self.db.scalar(select(AIProvider).where(AIProvider.id == provider_id, AIProvider.user_id == user_id))
        if not row:
            raise LookupError("AI provider not found")
        return row

    @staticmethod
    def _response(row: AIProvider) -> AIProviderResponse:
        secret = decrypt_secret(row.encrypted_api_key)
        masked = "••••" + secret[-4:] if len(secret) >= 4 else "••••"
        return AIProviderResponse(id=row.id, name=row.name, provider_type=row.provider_type, base_url=row.base_url,
                                  masked_api_key=masked, is_local=row.is_local, enabled=row.enabled,
                                  timeout_seconds=row.timeout_seconds, max_concurrency=row.max_concurrency,
                                  capabilities=row.capabilities, created_at=row.created_at, updated_at=row.updated_at)

    @staticmethod
    def _validate_url(value: str, is_local: bool) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Provider Base URL is invalid")
        if parsed.scheme == "http" and not is_local:
            raise ValueError("Cloud Provider must use HTTPS")
        host = parsed.hostname.lower()
        if host in {"metadata.google.internal", "169.254.169.254"}:
            raise ValueError("Provider address is not allowed")
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(host))
        except (ValueError, socket.gaierror):
            return
        if not is_local and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
            raise ValueError("Cloud Provider cannot target a private network")
