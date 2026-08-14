"""Async task: generate embeddings for chunks (implement in S10)."""

import uuid

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models import Chunk, Document
from app.processors.embedding import embedding_service


async def embed_document_chunks(document_id: uuid.UUID) -> None:
    """Generate and store embeddings for all chunks in a document."""
    async with async_session_factory() as db:
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        result = await db.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            return

        texts = [c.content for c in chunks]
        embeddings = embedding_service.embed_batch(texts)

        if embeddings is None:
            return  # Model not available

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        await db.commit()
