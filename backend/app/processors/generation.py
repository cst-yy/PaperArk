"""Generation provider protocol and OpenAI-compatible HTTP adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict

import httpx

from app.core.config import settings
from app.core.exceptions import GenerationProviderError


class GenerationMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    model: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class GenerationProvider(Protocol):
    model_name: str

    async def generate(
        self,
        messages: list[GenerationMessage],
        temperature: float,
        max_tokens: int,
    ) -> GenerationResult: ...


class OpenAICompatibleGenerationProvider:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
    ):
        self.base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.AI_API_KEY
        self.model_name = model_name or settings.AI_MODEL

    async def generate(
        self,
        messages: list[GenerationMessage],
        temperature: float,
        max_tokens: int,
    ) -> GenerationResult:
        if not self.api_key:
            raise GenerationProviderError("AI_API_KEY is not configured")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            choice = payload["choices"][0]
            text = choice["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("empty generation content")
            usage = payload.get("usage") or {}
            return GenerationResult(
                text=text.strip(),
                model=str(payload.get("model") or self.model_name),
                finish_reason=choice.get("finish_reason"),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
        except GenerationProviderError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationProviderError("Generation provider request failed", detail=str(exc)) from exc
