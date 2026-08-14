from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Chunk, Document, Note, Paper, Section
from app.processors.embedding import EmbeddingProvider
from app.services.search_query import normalize_note_search_text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_chunk_embedding_text(chunk: Chunk, section_title: str | None = None) -> str:
    return _normalize("\n".join(value for value in (section_title, chunk.content) if value))


def build_note_embedding_text(note: Note) -> str:
    return _normalize(f"{note.title}\n{normalize_note_search_text(note.content_markdown)}")


def embedding_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class RebuildResult:
    processed: int = 0
    skipped: int = 0
    failed: int = 0


class EmbeddingLifecycleService:
    def __init__(self, db: AsyncSession, provider: EmbeddingProvider, batch_size: int | None = None):
        self.db = db
        self.provider = provider
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        if provider.dimension != settings.EMBEDDING_DIMENSION:
            raise ValueError(f"Provider dimension {provider.dimension} does not match workspace dimension {settings.EMBEDDING_DIMENSION}")

    async def rebuild(self, user_id: uuid.UUID) -> RebuildResult:
        result = RebuildResult()
        chunk_rows = (await self.db.execute(select(Chunk, Section.title)
            .join(Document, Document.id == Chunk.document_id)
            .join(Paper, Paper.id == Document.paper_id)
            .outerjoin(Section, Section.id == Chunk.section_id)
            .where(Paper.user_id == user_id).order_by(Chunk.document_id, Chunk.chunk_index))).all()
        notes = list((await self.db.execute(select(Note).where(Note.user_id == user_id).order_by(Note.id))).scalars().all())
        candidates: list[tuple[Chunk | Note, str, str]] = []
        for chunk, section_title in chunk_rows:
            text = build_chunk_embedding_text(chunk, section_title)
            candidates.append((chunk, text, embedding_content_hash(text)))
        for note in notes:
            text = build_note_embedding_text(note)
            candidates.append((note, text, embedding_content_hash(text)))

        stale = []
        for entity, text, digest in candidates:
            if (entity.embedding_status == "ready" and entity.embedding_model == self.provider.model_name
                    and entity.embedding_dimension == self.provider.dimension
                    and entity.embedding_content_hash == digest and entity.embedding is not None):
                result.skipped += 1
            else:
                entity.embedding_status = "processing"
                entity.embedding_error = None
                stale.append((entity, text, digest))
        await self.db.commit()

        for start in range(0, len(stale), self.batch_size):
            batch = stale[start:start + self.batch_size]
            try:
                vectors = await self.provider.embed_documents([text for _, text, _ in batch])
                if len(vectors) != len(batch) or any(len(vector) != self.provider.dimension for vector in vectors):
                    raise RuntimeError("Embedding provider returned an invalid batch shape")
                for (entity, _, digest), vector in zip(batch, vectors):
                    entity.embedding = vector
                    entity.embedding_model = self.provider.model_name
                    entity.embedding_dimension = self.provider.dimension
                    entity.embedding_content_hash = digest
                    entity.embedding_status = "ready"
                    entity.embedding_error = None
                    result.processed += 1
            except Exception as exc:
                message = str(exc)[:2000]
                for entity, _, _ in batch:
                    entity.embedding_status = "failed"
                    entity.embedding_error = message
                    result.failed += 1
            await self.db.commit()
        return result

    async def status(self, user_id: uuid.UUID) -> dict[str, dict[str, int]]:
        output = {}
        chunk_rows = (await self.db.execute(select(Chunk.embedding_status, func.count())
            .join(Document, Document.id == Chunk.document_id).join(Paper, Paper.id == Document.paper_id)
            .where(Paper.user_id == user_id).group_by(Chunk.embedding_status))).all()
        note_rows = (await self.db.execute(select(Note.embedding_status, func.count())
            .where(Note.user_id == user_id).group_by(Note.embedding_status))).all()
        for name, rows in (("chunk", chunk_rows), ("note", note_rows)):
            counts = {state: 0 for state in ("pending", "processing", "ready", "failed")}
            counts.update({state: count for state, count in rows})
            output[name] = counts
        return output
