from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DuplicatePaperRelationError, InvalidPaperRelationError, PaperNotFoundError
from app.models import Chunk, Document, Paper, PaperRelation, PaperRelationSuggestion
from app.processors.generation import GenerationProvider
from app.schemas.knowledge_relation import AIRelationDecision, RelationSuggestionResponse
from app.services.search_service import SearchService


class RelationSuggestionService:
    def __init__(self, db: AsyncSession, provider: GenerationProvider):
        self.db, self.provider = db, provider

    async def generate(self, user_id: uuid.UUID, source_id: uuid.UUID, max_candidates: int):
        source = await self._paper(user_id, source_id)
        query = " ".join(filter(None, [source.title, source.abstract or ""]))[:2000]
        search = await SearchService(self.db).search(user_id, query, 1, max_candidates + 5, "hybrid")
        candidate_ids = [item.paper.id for item in search.items if item.entity_type == "paper" and item.paper.id != source_id][:max_candidates]
        candidates = list((await self.db.scalars(select(Paper).where(
            Paper.user_id == user_id, Paper.id.in_(candidate_ids)))).all())
        candidate_map = {item.id: item for item in candidates}
        created = []
        source_context = await self._context(user_id, source_id, "S")
        for target_id in candidate_ids:
            target = candidate_map.get(target_id)
            if target is None: continue
            target_context = await self._context(user_id, target_id, "T")
            known = {item["label"]: item for item in [*source_context, *target_context]}
            if not source_context or not target_context: continue
            result = await self.provider.generate(self._prompt(source, target, source_context, target_context),
                settings.AI_TEMPERATURE, settings.AI_MAX_OUTPUT_TOKENS)
            decision = self._parse(result.text)
            if decision.relation_type == "none": continue
            valid_refs = list(dict.fromkeys(ref for ref in decision.evidence_refs if ref in known))
            if not valid_refs or not any(ref.startswith("S") for ref in valid_refs) or not any(ref.startswith("T") for ref in valid_refs):
                continue
            evidence = [{**known[ref], "content_hash": hashlib.sha256(known[ref]["content"].encode()).hexdigest()} for ref in valid_refs]
            suggestion = PaperRelationSuggestion(user_id=user_id, source_paper_id=source_id,
                target_paper_id=target_id, relation_type=decision.relation_type,
                confidence=decision.confidence, reason=decision.reason, evidence_json=evidence,
                provider_name=getattr(self.provider, "provider_name", "unknown"), model=result.model)
            self.db.add(suggestion); await self.db.flush(); created.append(suggestion)
        return [self._response(item) for item in created]

    async def list(self, user_id, paper_id):
        await self._paper(user_id, paper_id)
        values = list((await self.db.scalars(select(PaperRelationSuggestion).where(
            PaperRelationSuggestion.user_id == user_id,
            (PaperRelationSuggestion.source_paper_id == paper_id) | (PaperRelationSuggestion.target_paper_id == paper_id)
        ).order_by(PaperRelationSuggestion.created_at.desc()))).all())
        return [self._response(item) for item in values]

    async def accept(self, user_id, suggestion_id):
        item = await self._suggestion(user_id, suggestion_id, lock=True)
        if item.status == "accepted": return self._response(item)
        if item.status != "pending": raise InvalidPaperRelationError("Rejected suggestion cannot be accepted")
        source_id, target_id = ((tuple(sorted((item.source_paper_id, item.target_paper_id), key=str)))
            if item.relation_type == "similar" else (item.source_paper_id, item.target_paper_id))
        relation = PaperRelation(user_id=user_id, source_paper_id=source_id, target_paper_id=target_id,
            relation_type=item.relation_type, origin="ai", confidence=item.confidence, note=item.reason)
        try:
            async with self.db.begin_nested():
                self.db.add(relation)
                await self.db.flush()
        except IntegrityError as exc: raise DuplicatePaperRelationError("Official relation already exists") from exc
        item.status, item.accepted_relation_id, item.decided_at = "accepted", relation.id, datetime.now(timezone.utc)
        await self.db.flush(); return self._response(item)

    async def reject(self, user_id, suggestion_id):
        item = await self._suggestion(user_id, suggestion_id, lock=True)
        if item.status == "rejected": return self._response(item)
        if item.status != "pending": raise InvalidPaperRelationError("Accepted suggestion cannot be rejected")
        item.status, item.decided_at = "rejected", datetime.now(timezone.utc)
        await self.db.flush(); return self._response(item)

    async def _paper(self, user_id, paper_id):
        item = await self.db.scalar(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
        if item is None: raise PaperNotFoundError("Paper not found")
        return item

    async def _suggestion(self, user_id, suggestion_id, lock=False):
        statement = select(PaperRelationSuggestion).where(PaperRelationSuggestion.id == suggestion_id,
            PaperRelationSuggestion.user_id == user_id)
        if lock: statement = statement.with_for_update()
        item = await self.db.scalar(statement)
        if item is None: raise InvalidPaperRelationError("Suggestion not found")
        return item

    async def _context(self, user_id, paper_id, prefix):
        rows = (await self.db.execute(select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
            .join(Paper, Document.paper_id == Paper.id).where(Paper.user_id == user_id, Paper.id == paper_id)
            .order_by(Chunk.chunk_index).limit(8))).all()
        return [{"label": f"{prefix}{index}", "paper_id": str(paper_id),
            "document_id": str(document.id), "section_id": str(chunk.section_id) if chunk.section_id else None,
            "chunk_id": str(chunk.id), "page_start": chunk.page_start,
            "page_end": chunk.page_end, "content": chunk.content}
            for index, (chunk, document) in enumerate(rows, 1)]

    @staticmethod
    def _prompt(source, target, source_context, target_context):
        contract = '{"relation_type":"extends|improves|contrasts|supports|uses|similar|none","confidence":0.0,"reason":"...","evidence_refs":["S1","T1"]}'
        context = "\n".join(f'[{item["label"]}] {item["content"]}' for item in [*source_context, *target_context])
        return [{"role":"system","content":"Compare only the supplied paper chunks. Return strict JSON. Use none when no defensible relation exists. Evidence must include valid refs from both S and T."},
            {"role":"user","content":f"Source: {source.title}\nTarget: {target.title}\nContract: {contract}\n{context}"}]

    @staticmethod
    def _parse(text):
        try: return AIRelationDecision.model_validate(json.loads(text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()))
        except (json.JSONDecodeError, ValidationError) as exc: raise InvalidPaperRelationError("AI relation output is invalid") from exc

    @staticmethod
    def _response(item):
        return RelationSuggestionResponse(id=item.id, source_paper_id=item.source_paper_id,
            target_paper_id=item.target_paper_id, relation_type=item.relation_type, status=item.status,
            confidence=item.confidence, reason=item.reason, evidence=item.evidence_json,
            provider_name=item.provider_name, model=item.model, accepted_relation_id=item.accepted_relation_id,
            created_at=item.created_at, decided_at=item.decided_at)
