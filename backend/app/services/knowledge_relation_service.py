from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicatePaperRelationError, InvalidPaperRelationError, PaperNotFoundError,
    PaperRelationNotFoundError,
)
from app.models import (
    Annotation, Document, Paper, PaperRelation, PaperRelationEvidence,
    PaperRelationSuggestion, Reference,
)
from app.schemas.knowledge_relation import (
    KnowledgeRelationResponse, ManualRelationCreate, ManualRelationUpdate,
    RelationEvidenceReplacement, RelationEvidenceResponse,
)


class KnowledgeRelationService:
    def __init__(self, db: AsyncSession): self.db = db

    async def create(self, user_id: uuid.UUID, source_id: uuid.UUID, data: ManualRelationCreate):
        source, target = await self._papers(user_id, source_id, data.target_paper_id)
        source_id, target_id = self._canonical(source.id, target.id, data.relation_type)
        relation = PaperRelation(user_id=user_id, source_paper_id=source_id, target_paper_id=target_id,
            relation_type=data.relation_type, origin="manual", note=data.note)
        try:
            async with self.db.begin_nested():
                self.db.add(relation)
                await self.db.flush()
        except IntegrityError as exc: raise DuplicatePaperRelationError("Relation already exists") from exc
        return await self._response(relation)

    async def update(self, user_id: uuid.UUID, paper_id: uuid.UUID, relation_id: uuid.UUID, data: ManualRelationUpdate):
        relation = await self._manual(user_id, paper_id, relation_id)
        await self._papers(user_id, paper_id, data.target_paper_id)
        source_id, target_id = self._canonical(paper_id, data.target_paper_id, data.relation_type)
        try:
            async with self.db.begin_nested():
                relation.source_paper_id, relation.target_paper_id = source_id, target_id
                relation.relation_type, relation.note = data.relation_type, data.note
                await self.db.flush()
        except IntegrityError as exc: raise DuplicatePaperRelationError("Relation already exists") from exc
        return await self._response(relation)

    async def delete(self, user_id: uuid.UUID, paper_id: uuid.UUID, relation_id: uuid.UUID) -> None:
        relation = await self._manual(user_id, paper_id, relation_id)
        await self.db.delete(relation)
        await self.db.flush()

    async def replace_evidence(self, user_id: uuid.UUID, relation_id: uuid.UUID, data: RelationEvidenceReplacement):
        relation = await self._owned(user_id, relation_id)
        if relation.origin == "reference":
            raise InvalidPaperRelationError("Reference citation evidence is system managed")
        allowed_papers = {relation.source_paper_id, relation.target_paper_id}
        snapshots: list[tuple[uuid.UUID | None, uuid.UUID | None, str]] = []
        for item in data.evidence:
            if item.annotation_id:
                annotation = await self.db.scalar(select(Annotation).where(
                    Annotation.id == item.annotation_id, Annotation.user_id == user_id,
                    Annotation.paper_id.in_(allowed_papers)))
                if annotation is None: raise InvalidPaperRelationError("Annotation evidence is not owned or outside the relation papers")
                quote = annotation.selected_text or annotation.comment or annotation.content or "Annotation"
                snapshots.append((annotation.id, None, quote))
            else:
                reference = await self.db.scalar(select(Reference).join(Document, Reference.document_id == Document.id)
                    .join(Paper, Document.paper_id == Paper.id).where(
                        Reference.id == item.source_reference_id, Paper.user_id == user_id,
                        Document.paper_id.in_(allowed_papers)))
                if reference is None: raise InvalidPaperRelationError("Reference evidence is not owned or outside the relation papers")
                snapshots.append((None, reference.id, reference.raw_text))
        async with self.db.begin_nested():
            await self.db.execute(delete(PaperRelationEvidence).where(PaperRelationEvidence.relation_id == relation.id))
            for index, (annotation_id, reference_id, quote) in enumerate(snapshots):
                self.db.add(PaperRelationEvidence(relation_id=relation.id, annotation_id=annotation_id,
                    source_reference_id=reference_id, quote_snapshot=quote, order_index=index))
            await self.db.flush()
        return await self._response(relation)

    async def get(self, user_id: uuid.UUID, relation_id: uuid.UUID):
        return await self._response(await self._owned(user_id, relation_id))

    async def _owned(self, user_id, relation_id):
        relation = await self.db.scalar(select(PaperRelation).where(PaperRelation.id == relation_id, PaperRelation.user_id == user_id))
        if relation is None: raise PaperRelationNotFoundError("Relation not found")
        return relation

    async def _manual(self, user_id, paper_id, relation_id):
        relation = await self._owned(user_id, relation_id)
        if relation.origin != "manual" or relation.relation_type == "cites":
            raise InvalidPaperRelationError("System and AI relations cannot be changed by manual CRUD")
        if paper_id != relation.source_paper_id and not (
            relation.relation_type == "similar" and paper_id == relation.target_paper_id
        ):
            raise PaperRelationNotFoundError("Relation not found")
        return relation

    async def _papers(self, user_id, source_id, target_id):
        if source_id == target_id: raise InvalidPaperRelationError("Self relations are not allowed")
        values = list((await self.db.scalars(select(Paper).where(Paper.user_id == user_id, Paper.id.in_([source_id, target_id])))).all())
        by_id = {item.id: item for item in values}
        if source_id not in by_id: raise PaperNotFoundError("Source paper not found")
        if target_id not in by_id: raise InvalidPaperRelationError("Target paper not found or belongs to another user")
        return by_id[source_id], by_id[target_id]

    @staticmethod
    def _canonical(source_id, target_id, relation_type):
        return tuple(sorted((source_id, target_id), key=str)) if relation_type == "similar" else (source_id, target_id)

    async def _response(self, relation):
        evidence = list((await self.db.scalars(select(PaperRelationEvidence).where(
            PaperRelationEvidence.relation_id == relation.id).order_by(PaperRelationEvidence.order_index))).all())
        suggestion = await self.db.scalar(select(PaperRelationSuggestion).where(
            PaperRelationSuggestion.accepted_relation_id == relation.id,
            PaperRelationSuggestion.status == "accepted",
        ).order_by(PaperRelationSuggestion.decided_at.desc()).limit(1))
        annotation_ids = {item.annotation_id for item in evidence if item.annotation_id}
        reference_ids = {item.source_reference_id for item in evidence if item.source_reference_id}
        annotations = {item.id: item for item in (await self.db.scalars(select(Annotation).where(
            Annotation.id.in_(annotation_ids)))).all()} if annotation_ids else {}
        reference_rows = (await self.db.execute(select(Reference, Document.paper_id).join(
            Document, Reference.document_id == Document.id).where(Reference.id.in_(reference_ids)))).all() if reference_ids else []
        references = {item.id: (item, paper_id) for item, paper_id in reference_rows}
        def evidence_response(item):
            annotation = annotations.get(item.annotation_id)
            reference_pair = references.get(item.source_reference_id)
            reference, reference_paper_id = reference_pair if reference_pair else (None, None)
            return RelationEvidenceResponse(id=item.id, annotation_id=item.annotation_id,
                source_reference_id=item.source_reference_id, quote_snapshot=item.quote_snapshot,
                order_index=item.order_index,
                paper_id=annotation.paper_id if annotation else reference_paper_id,
                document_id=annotation.document_id if annotation else reference.document_id if reference else None,
                page_number=annotation.page_number if annotation else reference.page_start if reference else None)
        return KnowledgeRelationResponse(id=relation.id, source_paper_id=relation.source_paper_id,
            target_paper_id=relation.target_paper_id, relation_type=relation.relation_type,
            origin=relation.origin, note=relation.note, confidence=relation.confidence,
            evidence=[evidence_response(item) for item in evidence],
            ai_evidence=suggestion.evidence_json if suggestion else [],
            ai_provider_name=suggestion.provider_name if suggestion else None,
            ai_model=suggestion.model if suggestion else None,
            created_at=relation.created_at)
