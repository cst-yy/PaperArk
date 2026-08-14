"""Search service - full-text and semantic search."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, Paper


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def full_text_search(
        self, user_id: uuid.UUID, query: str, limit: int = 20
    ) -> list[dict]:
        """Search across paper metadata and chunk content."""
        results: list[dict] = []
        pattern = f"%{query}%"

        # Search paper titles and abstracts
        stmt = (
            select(Paper)
            .where(
                Paper.user_id == user_id,
                (Paper.title.ilike(pattern)) | (Paper.abstract.ilike(pattern)),
            )
            .limit(limit)
        )
        paper_result = await self.db.execute(stmt)
        for paper in paper_result.scalars():
            results.append({
                "paper_id": str(paper.id),
                "title": paper.title,
                "snippet": (paper.abstract or "")[:200],
                "score": 1.0,
                "source": "metadata",
            })

        # Search chunk content (full-text in PDF)
        if len(results) < limit:
            remaining = limit - len(results)
            chunk_stmt = (
                select(Chunk, Document, Paper)
                .join(Document, Document.id == Chunk.document_id)
                .join(Paper, Paper.id == Document.paper_id)
                .where(
                    Paper.user_id == user_id,
                    Chunk.content.ilike(pattern),
                )
                .limit(remaining)
            )
            chunk_result = await self.db.execute(chunk_stmt)
            for chunk, doc, paper in chunk_result:
                content = chunk.content
                idx = content.lower().find(query.lower())
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 100)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                results.append({
                    "paper_id": str(paper.id),
                    "title": paper.title,
                    "snippet": snippet,
                    "page_number": chunk.page_number,
                    "score": 0.8,
                    "source": "chunk",
                })

        return results

    async def semantic_search(
        self, user_id: uuid.UUID, query: str, limit: int = 10
    ) -> list[dict]:
        """Vector similarity search using pgvector (implement in S10)."""
        # TODO: Implement in Sprint 10
        # 1. Embed the query
        # 2. SELECT * FROM chunks ORDER BY embedding <-> query_embedding LIMIT k
        return []
