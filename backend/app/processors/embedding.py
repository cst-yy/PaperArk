"""Versioned embedding provider abstraction and OpenAI-compatible adapter."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import settings


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None,
                 model_name: str | None = None, dimension: int | None = None):
        self.base_url = (base_url or settings.EMBEDDING_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.EMBEDDING_API_KEY
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("EMBEDDING_API_KEY is not configured")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model_name, "input": texts, "dimensions": self.dimension}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
            response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]
        if len(vectors) != len(texts) or any(len(vector) != self.dimension for vector in vectors):
            raise RuntimeError("Embedding provider returned an invalid batch shape")
        return vectors
