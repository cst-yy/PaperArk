from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import SemanticRetrievalError
from app.models import Chunk, Document, Note, Paper
from app.processors.embedding import EmbeddingProvider
from app.schemas.search import SearchHit
from app.services.search_query import QueryNormalizer, build_snippet


class SemanticQueryService:
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider
        if provider.dimension != settings.EMBEDDING_DIMENSION:
            raise SemanticRetrievalError(
                f"Embedding provider dimension {provider.dimension} does not match workspace dimension {settings.EMBEDDING_DIMENSION}"
            )

    async def embed_query(self, query: str) -> tuple[str, list[float]]:
        normalized = QueryNormalizer.normalize(query).normalized
        try:
            vectors = await self.provider.embed_documents([normalized])
        except Exception as exc:
            raise SemanticRetrievalError("Semantic embedding provider is unavailable", detail=str(exc)) from exc
        if len(vectors) != 1 or len(vectors[0]) != self.provider.dimension:
            raise SemanticRetrievalError("Embedding provider returned an invalid query vector dimension")
        return normalized, vectors[0]


class ChunkSemanticSearchProvider:
    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: str,
                     vector: list[float], provider: EmbeddingProvider) -> list[SearchHit]:
        distance = Chunk.embedding.cosine_distance(vector)
        rows = (await db.execute(select(Chunk, Document.paper_id, distance.label("distance"))
            .join(Document, Document.id == Chunk.document_id)
            .join(Paper, Paper.id == Document.paper_id)
            .where(Paper.user_id == user_id, Chunk.embedding.is_not(None),
                Chunk.embedding_status == "ready", Chunk.embedding_model == provider.model_name,
                Chunk.embedding_dimension == provider.dimension,
                distance <= 1.0 - settings.SEMANTIC_MIN_SIMILARITY)
            .order_by(distance).limit(settings.SEMANTIC_CANDIDATE_K))).all()
        return [SearchHit(paper_id=paper_id, document_id=chunk.document_id, source="chunk",
            retrieval_method="semantic", text=chunk.content,
            snippet=build_snippet(chunk.content, QueryNormalizer.normalize(query)),
            page_start=chunk.page_start or chunk.page_number,
            page_end=chunk.page_end or chunk.page_number, section_id=chunk.section_id,
            raw_score=max(0.0, 1.0 - float(distance))) for chunk, paper_id, distance in rows]


class NoteSemanticSearchProvider:
    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: str,
                     vector: list[float], provider: EmbeddingProvider) -> list[SearchHit]:
        distance = Note.embedding.cosine_distance(vector)
        rows = (await db.execute(select(Note, distance.label("distance"))
            .where(Note.user_id == user_id, Note.embedding.is_not(None),
                Note.embedding_status == "ready", Note.embedding_model == provider.model_name,
                Note.embedding_dimension == provider.dimension,
                distance <= 1.0 - settings.SEMANTIC_MIN_SIMILARITY)
            .order_by(distance).limit(settings.SEMANTIC_CANDIDATE_K))).all()
        return [SearchHit(entity_type="note", note_id=note.id, paper_id=note.paper_id,
            source="note_content", retrieval_method="semantic", text=note.content_markdown or note.title,
            snippet=build_snippet(note.content_markdown or note.title, QueryNormalizer.normalize(query)),
            raw_score=max(0.0, 1.0 - float(distance))) for note, distance in rows]
