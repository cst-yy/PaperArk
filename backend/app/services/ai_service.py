"""AI service - LLM integration for summary, Q&A, and concept extraction."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Chunk, Document, Paper


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_paper_context(
        self, paper_id: uuid.UUID, max_chunks: int = 10
    ) -> list[Chunk]:
        """Retrieve relevant chunks for a paper (context for LLM)."""
        stmt = (
            select(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.paper_id == paper_id)
            .order_by(Chunk.chunk_index)
            .limit(max_chunks)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def generate_summary(self, paper_id: uuid.UUID) -> dict[str, Any]:
        """Generate a paper summary using LLM (implement in S11)."""
        paper = await self.db.get(Paper, paper_id)
        if not paper:
            return {"error": "Paper not found"}

        chunks = await self.get_paper_context(paper_id)
        context = "\n\n".join(c.content for c in chunks[:5])

        if not settings.OPENAI_API_KEY:
            return {
                "tldr": "[Set OPENAI_API_KEY to enable AI summary]",
                "key_points": [],
                "context_length": len(context),
            }

        # TODO: Call OpenAI API in Sprint 11
        # response = await openai_client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a research paper assistant..."},
        #         {"role": "user", "content": f"Summarize this paper:\n\n{context}"},
        #     ],
        # )
        return {
            "tldr": "[AI summary - implement in Sprint 11]",
            "key_points": [],
            "context_length": len(context),
        }

    async def answer_question(
        self, paper_id: uuid.UUID, question: str
    ) -> dict[str, Any]:
        """Answer a question about a paper using RAG (implement in S11)."""
        if not settings.OPENAI_API_KEY:
            return {
                "answer": "[Set OPENAI_API_KEY to enable AI Q&A]",
                "sources": [],
            }

        # TODO: Implement RAG pipeline in Sprint 11
        # 1. Embed question
        # 2. Vector search chunks
        # 3. Build context
        # 4. Call LLM
        # 5. Return answer with source citations
        return {
            "answer": "[AI Q&A - implement in Sprint 11]",
            "sources": [],
        }

    async def extract_concepts(self, paper_id: uuid.UUID) -> list[str]:
        """Extract key concepts from a paper (implement in S11)."""
        # TODO: Implement in Sprint 11
        return []
