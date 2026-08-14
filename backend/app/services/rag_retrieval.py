from __future__ import annotations

import uuid
from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import RAGContextError, SemanticRetrievalError
from app.models import Chunk, Document, Note, Paper, Section
from app.processors.embedding import EmbeddingProvider, OpenAICompatibleEmbeddingProvider
from app.services.rag_context import RAGCandidate
from app.services.search_query import QueryNormalizer, normalize_note_search_text
from app.services.semantic_search import SemanticQueryService


class RAGRetrievalService:
    def __init__(self, db: AsyncSession, provider: EmbeddingProvider | None = None):
        self.db = db
        self.provider = provider or OpenAICompatibleEmbeddingProvider()

    async def _validate_scope(self, user_id: uuid.UUID, paper_id: uuid.UUID | None) -> None:
        if paper_id is not None and not await self.db.scalar(select(Paper.id).where(Paper.id == paper_id, Paper.user_id == user_id)):
            raise RAGContextError("Paper does not exist or belongs to another user")

    async def lexical(self, user_id: uuid.UUID, query: str, paper_id: uuid.UUID | None) -> list[RAGCandidate]:
        normalized = QueryNormalizer.normalize(query).normalized
        tsquery = func.websearch_to_tsquery("simple", normalized)
        chunk_rank = func.ts_rank_cd(Chunk.search_vector, tsquery)
        chunk_stmt = (select(Chunk, Document.paper_id, Paper.title, Section.title, chunk_rank)
            .join(Document, Document.id == Chunk.document_id).join(Paper, Paper.id == Document.paper_id)
            .outerjoin(Section, Section.id == Chunk.section_id)
            .where(Paper.user_id == user_id, Chunk.search_vector.op("@@")(tsquery)))
        if paper_id is not None: chunk_stmt = chunk_stmt.where(Paper.id == paper_id)
        chunk_rows = (await self.db.execute(chunk_stmt.order_by(chunk_rank.desc(), Chunk.id).limit(settings.RAG_CANDIDATE_K))).all()
        candidates = [RAGCandidate(source_key=f"chunk:{chunk.id}", source_type="paper_chunk",
            title=paper_title, content=chunk.content, paper_id=pid, paper_title=paper_title,
            document_id=chunk.document_id, section_id=chunk.section_id, section_title=section_title,
            page_start=chunk.page_start or chunk.page_number, page_end=chunk.page_end or chunk.page_number,
            chunk_index=chunk.chunk_index, retrieval_method="lexical", retrieval_score=float(rank or 0),
            lexical_rank=index) for index, (chunk, pid, paper_title, section_title, rank) in enumerate(chunk_rows, 1)]
        note_rank = func.ts_rank_cd(Note.search_vector, tsquery)
        note_stmt = (select(Note, Paper.title, note_rank).outerjoin(Paper, Paper.id == Note.paper_id)
            .where(Note.user_id == user_id, Note.search_vector.op("@@")(tsquery)))
        if paper_id is not None: note_stmt = note_stmt.where(Note.paper_id == paper_id)
        note_rows = (await self.db.execute(note_stmt.order_by(note_rank.desc(), Note.id).limit(settings.RAG_CANDIDATE_K))).all()
        candidates.extend(RAGCandidate(source_key=f"note:{note.id}", source_type="note", title=note.title,
            content=normalize_note_search_text(note.content_markdown), paper_id=note.paper_id,
            paper_title=paper_title, note_id=note.id, retrieval_method="lexical",
            retrieval_score=float(rank or 0), lexical_rank=index)
            for index, (note, paper_title, rank) in enumerate(note_rows, 1))
        return sorted(candidates, key=lambda item: (-item.retrieval_score, item.source_type, item.source_key))

    async def semantic(self, user_id: uuid.UUID, query: str, paper_id: uuid.UUID | None) -> list[RAGCandidate]:
        normalized, vector = await SemanticQueryService(self.provider).embed_query(query)
        del normalized
        distance = Chunk.embedding.cosine_distance(vector)
        chunk_stmt = (select(Chunk, Document.paper_id, Paper.title, Section.title, distance)
            .join(Document, Document.id == Chunk.document_id).join(Paper, Paper.id == Document.paper_id)
            .outerjoin(Section, Section.id == Chunk.section_id)
            .where(Paper.user_id == user_id, Chunk.embedding.is_not(None), Chunk.embedding_status == "ready",
                Chunk.embedding_model == self.provider.model_name, Chunk.embedding_dimension == self.provider.dimension,
                distance <= 1 - settings.SEMANTIC_MIN_SIMILARITY))
        if paper_id is not None: chunk_stmt = chunk_stmt.where(Paper.id == paper_id)
        chunk_rows = (await self.db.execute(chunk_stmt.order_by(distance, Chunk.id).limit(settings.RAG_CANDIDATE_K))).all()
        candidates = [RAGCandidate(source_key=f"chunk:{chunk.id}", source_type="paper_chunk", title=title,
            content=chunk.content, paper_id=pid, paper_title=title, document_id=chunk.document_id,
            section_id=chunk.section_id, section_title=section_title,
            page_start=chunk.page_start or chunk.page_number, page_end=chunk.page_end or chunk.page_number,
            chunk_index=chunk.chunk_index, retrieval_method="semantic", retrieval_score=1-float(dist),
            semantic_rank=index) for index, (chunk, pid, title, section_title, dist) in enumerate(chunk_rows, 1)]
        note_distance = Note.embedding.cosine_distance(vector)
        note_stmt = (select(Note, Paper.title, note_distance).outerjoin(Paper, Paper.id == Note.paper_id)
            .where(Note.user_id == user_id, Note.embedding.is_not(None), Note.embedding_status == "ready",
                Note.embedding_model == self.provider.model_name, Note.embedding_dimension == self.provider.dimension,
                note_distance <= 1 - settings.SEMANTIC_MIN_SIMILARITY))
        if paper_id is not None: note_stmt = note_stmt.where(Note.paper_id == paper_id)
        note_rows = (await self.db.execute(note_stmt.order_by(note_distance, Note.id).limit(settings.RAG_CANDIDATE_K))).all()
        candidates.extend(RAGCandidate(source_key=f"note:{note.id}", source_type="note", title=note.title,
            content=normalize_note_search_text(note.content_markdown), paper_id=note.paper_id,
            paper_title=title, note_id=note.id, retrieval_method="semantic",
            retrieval_score=1-float(dist), semantic_rank=index)
            for index, (note, title, dist) in enumerate(note_rows, 1))
        return sorted(candidates, key=lambda item: (-item.retrieval_score, item.source_type, item.source_key))

    @staticmethod
    def fuse(lexical: list[RAGCandidate], semantic: list[RAGCandidate]) -> list[RAGCandidate]:
        left = {item.source_key: (index, item) for index, item in enumerate(lexical, 1)}
        right = {item.source_key: (index, item) for index, item in enumerate(semantic, 1)}
        output = []
        for key in left.keys() | right.keys():
            lexical_rank = left.get(key, (None, None))[0]
            semantic_rank = right.get(key, (None, None))[0]
            score = (1/(settings.HYBRID_RRF_K + lexical_rank) if lexical_rank else 0) + (1/(settings.HYBRID_RRF_K + semantic_rank) if semantic_rank else 0)
            candidate = left[key][1] if key in left else right[key][1]
            output.append(replace(candidate, retrieval_method="hybrid", retrieval_score=score,
                lexical_rank=lexical_rank, semantic_rank=semantic_rank))
        return sorted(output, key=lambda item: (-item.retrieval_score,
            item.lexical_rank is None, item.lexical_rank or 10**9,
            item.semantic_rank is None, item.semantic_rank or 10**9, item.source_key))

    async def retrieve(self, user_id: uuid.UUID, query: str, mode: str,
                       paper_id: uuid.UUID | None) -> tuple[list[RAGCandidate], str, bool, bool]:
        await self._validate_scope(user_id, paper_id)
        if mode == "lexical": return await self.lexical(user_id, query, paper_id), "lexical", True, False
        index_ready = await self._semantic_index_ready(user_id, paper_id)
        if mode == "semantic": return await self.semantic(user_id, query, paper_id), "semantic", True, index_ready
        lexical = await self.lexical(user_id, query, paper_id)
        try:
            semantic = await self.semantic(user_id, query, paper_id)
        except SemanticRetrievalError:
            return lexical, "lexical", False, False
        return self.fuse(lexical, semantic), "hybrid" if index_ready else "lexical", True, index_ready

    async def _semantic_index_ready(self, user_id: uuid.UUID, paper_id: uuid.UUID | None) -> bool:
        chunk_stmt = (select(func.count()).select_from(Chunk).join(Document, Document.id == Chunk.document_id)
            .join(Paper, Paper.id == Document.paper_id).where(Paper.user_id == user_id,
                Chunk.embedding_status == "ready", Chunk.embedding_model == self.provider.model_name,
                Chunk.embedding_dimension == self.provider.dimension, Chunk.embedding.is_not(None)))
        if paper_id is not None: chunk_stmt = chunk_stmt.where(Paper.id == paper_id)
        if await self.db.scalar(chunk_stmt): return True
        note_stmt = select(func.count()).select_from(Note).where(Note.user_id == user_id,
            Note.embedding_status == "ready", Note.embedding_model == self.provider.model_name,
            Note.embedding_dimension == self.provider.dimension, Note.embedding.is_not(None))
        if paper_id is not None: note_stmt = note_stmt.where(Note.paper_id == paper_id)
        return bool(await self.db.scalar(note_stmt))
