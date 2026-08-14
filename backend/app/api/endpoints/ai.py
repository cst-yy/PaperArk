import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DEFAULT_USER_ID, get_db
from app.models import Chunk, Document, Paper
from pydantic import BaseModel

router = APIRouter()


class SummaryRequest(BaseModel):
    paper_id: uuid.UUID


class SummaryResponse(BaseModel):
    paper_id: uuid.UUID
    tldr: str
    key_points: list[str]
    methods: str | None = None
    contribution: str | None = None


class QARequest(BaseModel):
    paper_id: uuid.UUID
    question: str


class QAResponse(BaseModel):
    paper_id: uuid.UUID
    question: str
    answer: str
    sources: list[dict] = []


@router.post("/summary", response_model=SummaryResponse)
async def get_summary(data: SummaryRequest, db: AsyncSession = Depends(get_db)):
    """Generate a paper summary (stub - integrate LLM in S11)."""
    paper = await db.get(Paper, data.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # TODO: Replace with actual LLM call in Sprint 11
    return SummaryResponse(
        paper_id=paper.id,
        tldr=f"[AI Summary placeholder] {paper.title[:100]}...",
        key_points=["Point 1 - to be filled by LLM", "Point 2 - to be filled by LLM"],
        methods=None,
        contribution=None,
    )


@router.post("/qa", response_model=QAResponse)
async def ask_question(data: QARequest, db: AsyncSession = Depends(get_db)):
    """Answer a question about a paper using RAG (stub - integrate in S11)."""
    paper = await db.get(Paper, data.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # TODO: Implement vector search + LLM in Sprint 11
    # 1. Embed the question
    # 2. Search chunks by similarity
    # 3. Feed context to LLM
    # 4. Return answer with source citations

    return QAResponse(
        paper_id=paper.id,
        question=data.question,
        answer="[AI Q&A placeholder - will be implemented in Sprint 11 with RAG pipeline]",
        sources=[],
    )


@router.post("/concepts")
async def extract_concepts(
    data: SummaryRequest, db: AsyncSession = Depends(get_db)
):
    """Extract key concepts and terms from a paper (stub)."""
    paper = await db.get(Paper, data.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # TODO: Implement concept extraction in Sprint 11
    return {
        "paper_id": str(paper.id),
        "concepts": [],
        "message": "Concept extraction will be implemented in Sprint 11",
    }
