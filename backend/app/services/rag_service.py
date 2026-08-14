import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.processors.embedding import EmbeddingProvider
from app.schemas.rag import RAGContextRequest, RAGContextResponse
from app.services.rag_context import RAGContextAssembler
from app.services.rag_retrieval import RAGRetrievalService


class RAGService:
    def __init__(self, db: AsyncSession, provider: EmbeddingProvider | None = None):
        self.retrieval = RAGRetrievalService(db, provider)
        self.assembler = RAGContextAssembler()

    async def build_context(self, user_id: uuid.UUID, request: RAGContextRequest) -> RAGContextResponse:
        candidates, effective, available, index_ready = await self.retrieval.retrieve(
            user_id, request.query, request.mode, request.paper_id)
        sources, context, tokens, truncated = self.assembler.assemble(candidates,
            max_sources=request.max_sources, token_budget=request.token_budget,
            paper_scope=request.paper_id is not None)
        return RAGContextResponse(query=request.query, requested_mode=request.mode,
            effective_mode=effective, degraded=request.mode != effective,
            semantic_available=available, semantic_index_ready=index_ready,
            sources=sources, context_text=context, estimated_tokens=tokens, truncated=truncated)
