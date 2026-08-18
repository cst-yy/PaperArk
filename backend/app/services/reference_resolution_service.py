from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Paper, Reference
from app.parsers.reference_matcher import ReferenceMatcher
from app.parsers.reference_metadata_parser import ParsedReference
from app.services.paper_relation_service import PaperRelationService


class ReferenceResolutionService:
    """Re-resolve durable Reference rows after library identity changes."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = ReferenceMatcher(db)

    async def resolve_workspace_for_paper_change(
        self, user_id: uuid.UUID, changed_paper_id: uuid.UUID
    ) -> set[uuid.UUID]:
        # The changed paper is validated by its owning PaperService before this
        # method is called. Re-evaluating all user references also clears matches
        # that became stale after DOI/arXiv/title edits.
        rows = (await self.db.execute(
            select(Reference, Document.paper_id)
            .join(Document, Reference.document_id == Document.id)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Paper.user_id == user_id)
            .order_by(Document.paper_id, Reference.document_id, Reference.order_index)
        )).all()
        affected: set[uuid.UUID] = set()
        for reference, source_paper_id in rows:
            match = await self.matcher.match(user_id, self._parsed(reference))
            if (reference.matched_paper_id, reference.match_method, reference.match_confidence) != (
                match.paper_id, match.method, match.confidence
            ):
                reference.matched_paper_id = match.paper_id
                reference.match_method = match.method
                reference.match_confidence = match.confidence
            affected.add(source_paper_id)
        await self.db.flush()
        relations = PaperRelationService(self.db)
        for source_paper_id in sorted(affected, key=str):
            await relations.sync_citations_for_paper(user_id, source_paper_id)
        return affected

    @staticmethod
    def _parsed(reference: Reference) -> ParsedReference:
        return ParsedReference(
            order_index=reference.order_index, raw_text=reference.raw_text,
            page_start=reference.page_start, page_end=reference.page_end,
            section_id=reference.section_id, title=reference.title,
            authors=reference.authors_json, year=reference.year, doi=reference.doi,
            arxiv_id=reference.arxiv_id, venue=reference.venue,
        )
