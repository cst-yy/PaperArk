from __future__ import annotations

import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, Paper, PaperRelation, Reference


class PaperRelationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def replace_reference_citations(
        self, user_id: uuid.UUID, source_paper_id: uuid.UUID, references: list[Reference]
    ) -> list[PaperRelation]:
        await self.db.execute(delete(PaperRelation).where(
            PaperRelation.user_id == user_id,
            PaperRelation.source_paper_id == source_paper_id,
            PaperRelation.relation_type == "cites",
            PaperRelation.origin == "reference",
        ))
        candidate_ids = {item.matched_paper_id for item in references if item.matched_paper_id}
        owned_target_ids = set((await self.db.scalars(select(Paper.id).where(
            Paper.user_id == user_id, Paper.id.in_(candidate_ids)
        ))).all()) if candidate_ids else set()
        seen: set[uuid.UUID] = set()
        created: list[PaperRelation] = []
        for reference in references:
            target_id = reference.matched_paper_id
            if target_id is None or target_id not in owned_target_ids or target_id == source_paper_id or target_id in seen:
                continue
            seen.add(target_id)
            relation = PaperRelation(
                user_id=user_id, source_paper_id=source_paper_id,
                target_paper_id=target_id, relation_type="cites", origin="reference",
                source_reference_id=reference.id, confidence=reference.match_confidence,
            )
            self.db.add(relation)
            created.append(relation)
        await self.db.flush()
        return created

    async def list_for_paper(
        self, user_id: uuid.UUID, paper_id: uuid.UUID
    ) -> tuple[list[PaperRelation], list[PaperRelation]]:
        options = (
            selectinload(PaperRelation.source_paper),
            selectinload(PaperRelation.target_paper),
        )
        relations = list((await self.db.scalars(
            select(PaperRelation).where(
                PaperRelation.user_id == user_id,
                PaperRelation.relation_type == "cites",
                PaperRelation.origin == "reference",
                or_(PaperRelation.source_paper_id == paper_id, PaperRelation.target_paper_id == paper_id),
            ).options(*options).order_by(PaperRelation.created_at, PaperRelation.id)
        )).all())
        return (
            [item for item in relations if item.target_paper_id == paper_id],
            [item for item in relations if item.source_paper_id == paper_id],
        )

    async def references_for_source(self, user_id: uuid.UUID, source_paper_id: uuid.UUID) -> list[Reference]:
        return list((await self.db.scalars(
            select(Reference)
            .join(Document, Reference.document_id == Document.id)
            .join(Paper, Document.paper_id == Paper.id)
            .where(Paper.user_id == user_id, Paper.id == source_paper_id)
            .order_by(Reference.document_id, Reference.order_index)
        )).all())
