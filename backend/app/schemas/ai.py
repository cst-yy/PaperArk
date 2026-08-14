from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.schemas.rag import RAGMode


class AICitation(BaseModel):
    label: str
    source_key: str
    source_type: Literal["paper_chunk", "note"]
    paper_id: UUID | None = None
    paper_title: str | None = None
    document_id: UUID | None = None
    note_id: UUID | None = None
    title: str
    section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class AIAnswer(BaseModel):
    answer: str
    citations: list[AICitation]
    grounded: bool
    insufficient_evidence: bool
    requested_mode: RAGMode
    effective_mode: RAGMode


class PaperQARequest(BaseModel):
    paper_id: UUID
    query: str = Field(min_length=1, max_length=2000)
    retrieval_mode: RAGMode = "hybrid"
    max_sources: int = Field(settings.RAG_DEFAULT_MAX_SOURCES, ge=1, le=20)
    token_budget: int = Field(
        settings.RAG_DEFAULT_TOKEN_BUDGET, ge=1000, le=settings.RAG_MAX_TOKEN_BUDGET
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class PaperQAResponse(AIAnswer):
    paper_id: UUID
    query: str


TargetLanguage = Literal["zh-CN", "en"]


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    target_language: TargetLanguage

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be blank")
        return normalized


class TranslationResult(BaseModel):
    translated_text: str
    source_language: str | None = None
    target_language: TargetLanguage
