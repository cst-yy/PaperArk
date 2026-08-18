from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models import (
    Paper, PaperAuthor, PaperRelation, PaperRelationEvidence, PaperRelationSuggestion,
)


class KnowledgeGraphRepository:
    def __init__(self, db: AsyncSession, relation_types: set[str], origins: set[str]):
        self.db = db
        self.relation_types = relation_types
        self.origins = origins

    def _scoped_edges(self, user_id: uuid.UUID):
        source, target = aliased(Paper), aliased(Paper)
        return (select(PaperRelation)
            .join(source, PaperRelation.source_paper_id == source.id)
            .join(target, PaperRelation.target_paper_id == target.id)
            .where(PaperRelation.user_id == user_id,
                PaperRelation.relation_type.in_(self.relation_types),
                PaperRelation.origin.in_(self.origins),
                source.user_id == user_id, target.user_id == user_id))

    async def root_exists(self, user_id, paper_id):
        return await self.db.scalar(select(Paper.id).where(Paper.id == paper_id, Paper.user_id == user_id)) is not None

    async def adjacent_edges(self, user_id, paper_ids):
        if not paper_ids: return []
        return list((await self.db.scalars(self._scoped_edges(user_id).where(or_(
            PaperRelation.source_paper_id.in_(paper_ids), PaperRelation.target_paper_id.in_(paper_ids))))).all())

    async def workspace_edges(self, user_id):
        return list((await self.db.scalars(self._scoped_edges(user_id))).all())

    async def induced_edges(self, user_id, paper_ids):
        if not paper_ids: return []
        return list((await self.db.scalars(self._scoped_edges(user_id).where(
            PaperRelation.source_paper_id.in_(paper_ids), PaperRelation.target_paper_id.in_(paper_ids)
        ).order_by(PaperRelation.source_paper_id, PaperRelation.target_paper_id, PaperRelation.id))).all())

    async def papers(self, user_id, paper_ids):
        if not paper_ids: return []
        return list((await self.db.scalars(select(Paper).where(Paper.user_id == user_id, Paper.id.in_(paper_ids))
            .options(selectinload(Paper.authors).selectinload(PaperAuthor.author)))).all())

    async def degree_counts(self, user_id, paper_ids):
        if not paper_ids: return {}, {}
        scoped = self._scoped_edges(user_id).subquery()
        outgoing = dict((await self.db.execute(select(scoped.c.source_paper_id, func.count()).where(
            scoped.c.source_paper_id.in_(paper_ids)).group_by(scoped.c.source_paper_id))).all())
        incoming = dict((await self.db.execute(select(scoped.c.target_paper_id, func.count()).where(
            scoped.c.target_paper_id.in_(paper_ids)).group_by(scoped.c.target_paper_id))).all())
        return incoming, outgoing

    async def evidence_counts(self, relation_ids):
        if not relation_ids: return {}
        counts = dict((await self.db.execute(select(PaperRelationEvidence.relation_id, func.count()).where(
            PaperRelationEvidence.relation_id.in_(relation_ids)).group_by(PaperRelationEvidence.relation_id))).all())
        ai_counts = dict((await self.db.execute(select(
            PaperRelationSuggestion.accepted_relation_id,
            func.json_array_length(PaperRelationSuggestion.evidence_json),
        ).where(
            PaperRelationSuggestion.accepted_relation_id.in_(relation_ids),
            PaperRelationSuggestion.status == "accepted",
        ))).all())
        for relation_id, value in ai_counts.items():
            counts[relation_id] = counts.get(relation_id, 0) + value
        return counts
