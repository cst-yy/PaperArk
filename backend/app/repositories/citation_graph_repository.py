from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models import Document, Paper, PaperAuthor, PaperRelation, Reference


class CitationGraphRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _scoped_edges(user_id: uuid.UUID):
        source = aliased(Paper)
        target = aliased(Paper)
        return (
            select(PaperRelation)
            .join(source, PaperRelation.source_paper_id == source.id)
            .join(target, PaperRelation.target_paper_id == target.id)
            .where(
                PaperRelation.user_id == user_id,
                PaperRelation.relation_type == "cites",
                PaperRelation.origin == "reference",
                source.user_id == user_id,
                target.user_id == user_id,
            )
        )

    async def root_exists(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> bool:
        return (await self.db.scalar(select(Paper.id).where(
            Paper.id == paper_id, Paper.user_id == user_id
        ))) is not None

    async def adjacent_edges(self, user_id: uuid.UUID, paper_ids: set[uuid.UUID]) -> list[PaperRelation]:
        if not paper_ids:
            return []
        return list((await self.db.scalars(self._scoped_edges(user_id).where(or_(
            PaperRelation.source_paper_id.in_(paper_ids), PaperRelation.target_paper_id.in_(paper_ids)
        )))).all())

    async def workspace_edges(self, user_id: uuid.UUID) -> list[PaperRelation]:
        return list((await self.db.scalars(self._scoped_edges(user_id))).all())

    async def induced_edges(self, user_id: uuid.UUID, paper_ids: set[uuid.UUID]) -> list[PaperRelation]:
        if not paper_ids:
            return []
        return list((await self.db.scalars(self._scoped_edges(user_id).where(
            PaperRelation.source_paper_id.in_(paper_ids),
            PaperRelation.target_paper_id.in_(paper_ids),
        ).order_by(PaperRelation.source_paper_id, PaperRelation.target_paper_id, PaperRelation.id))).all())

    async def papers(self, user_id: uuid.UUID, paper_ids: set[uuid.UUID]) -> list[Paper]:
        if not paper_ids:
            return []
        return list((await self.db.scalars(
            select(Paper).where(Paper.user_id == user_id, Paper.id.in_(paper_ids))
            .options(selectinload(Paper.authors).selectinload(PaperAuthor.author))
        )).all())

    async def degree_counts(
        self, user_id: uuid.UUID, paper_ids: set[uuid.UUID]
    ) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
        if not paper_ids:
            return {}, {}
        scoped = self._scoped_edges(user_id).subquery()
        outgoing = dict((await self.db.execute(
            select(scoped.c.source_paper_id, func.count()).where(
                scoped.c.source_paper_id.in_(paper_ids)
            ).group_by(scoped.c.source_paper_id)
        )).all())
        incoming = dict((await self.db.execute(
            select(scoped.c.target_paper_id, func.count()).where(
                scoped.c.target_paper_id.in_(paper_ids)
            ).group_by(scoped.c.target_paper_id)
        )).all())
        return incoming, outgoing

    async def edge_with_reference(
        self, user_id: uuid.UUID, relation_id: uuid.UUID
    ) -> tuple[PaperRelation, Reference | None] | None:
        relation = await self.db.scalar(self._scoped_edges(user_id).where(PaperRelation.id == relation_id))
        if relation is None:
            return None
        reference = None
        if relation.source_reference_id:
            reference = await self.db.scalar(
                select(Reference)
                .join(Document, Reference.document_id == Document.id)
                .join(Paper, Document.paper_id == Paper.id)
                .where(
                    Reference.id == relation.source_reference_id,
                    Document.paper_id == relation.source_paper_id,
                    Paper.user_id == user_id,
                )
            )
        return relation, reference
