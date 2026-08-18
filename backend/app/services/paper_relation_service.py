from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.models import PaperRelation
from app.repositories.paper_relation_repository import PaperRelationRepository
from app.repositories.paper_repository import PaperRepository
from app.schemas.paper_relation import PaperRelationResponse, PaperRelationsResponse, RelatedPaperBrief


class PaperRelationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaperRelationRepository(db)
        self.papers = PaperRepository(db)

    async def sync_citations_for_paper(
        self, user_id: uuid.UUID, source_paper_id: uuid.UUID
    ) -> list[PaperRelation]:
        if await self.papers.get_raw(source_paper_id, user_id) is None:
            raise PaperNotFoundError("Paper not found")
        references = await self.repo.references_for_source(user_id, source_paper_id)
        return await self.repo.replace_reference_citations(user_id, source_paper_id, references)

    async def get_relations(
        self, user_id: uuid.UUID, paper_id: uuid.UUID
    ) -> PaperRelationsResponse:
        if await self.papers.get_raw(paper_id, user_id) is None:
            raise PaperNotFoundError("Paper not found")
        incoming, outgoing = await self.repo.list_for_paper(user_id, paper_id)
        return PaperRelationsResponse(
            paper_id=paper_id, incoming_count=len(incoming), outgoing_count=len(outgoing),
            incoming=[self._response(item, item.source_paper) for item in incoming],
            outgoing=[self._response(item, item.target_paper) for item in outgoing],
        )

    @staticmethod
    def _response(relation: PaperRelation, related) -> PaperRelationResponse:
        return PaperRelationResponse(
            id=relation.id, source_paper_id=relation.source_paper_id,
            target_paper_id=relation.target_paper_id, relation_type="cites", origin="reference",
            source_reference_id=relation.source_reference_id, confidence=relation.confidence,
            related_paper=RelatedPaperBrief(
                id=related.id, title=related.title, publication_year=related.publication_year
            ), created_at=relation.created_at,
        )
