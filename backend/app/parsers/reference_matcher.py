"""User-scoped deterministic matching of references to imported library papers."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Paper
from app.parsers.reference_metadata_parser import ParsedReference, normalize_arxiv_id, normalize_doi


@dataclass(frozen=True)
class ReferenceMatch:
    paper_id: uuid.UUID | None = None
    method: str | None = None
    confidence: float | None = None


def normalize_title(raw: str | None) -> str | None:
    if not raw:
        return None
    normalized = re.sub(r"[^\w]+", " ", raw.casefold(), flags=re.UNICODE).strip()
    return normalized or None


class ReferenceMatcher:
    """Match only within the owner library; it never creates PaperRelation rows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def match(self, user_id: uuid.UUID, reference: ParsedReference) -> ReferenceMatch:
        if reference.doi:
            paper = await self._by_doi(user_id, reference.doi)
            if paper:
                return ReferenceMatch(paper.id, "doi", 1.0)
        if reference.arxiv_id:
            paper = await self._by_arxiv(user_id, reference.arxiv_id)
            if paper:
                return ReferenceMatch(paper.id, "arxiv", 1.0)
        if reference.title:
            paper = await self._by_exact_title(user_id, reference.title)
            if paper:
                return ReferenceMatch(paper.id, "title_exact", 0.95)
        return ReferenceMatch()

    async def _by_doi(self, user_id: uuid.UUID, doi: str) -> Paper | None:
        stmt = select(Paper).where(
            Paper.user_id == user_id,
            func.lower(Paper.doi) == normalize_doi(doi),
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _by_arxiv(self, user_id: uuid.UUID, arxiv_id: str) -> Paper | None:
        stmt = select(Paper).where(
            Paper.user_id == user_id,
            func.lower(Paper.arxiv_id) == normalize_arxiv_id(arxiv_id),
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _by_exact_title(self, user_id: uuid.UUID, title: str) -> Paper | None:
        target = normalize_title(title)
        if not target:
            return None
        papers = (await self.db.execute(select(Paper).where(Paper.user_id == user_id))).scalars().all()
        return next((paper for paper in papers if normalize_title(paper.title) == target), None)
