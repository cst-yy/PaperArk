"""Paper-level search aggregation for the stable S8-A contract."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import SemanticRetrievalError
from app.models import Chunk, Document, Note, Paper, PaperAuthor
from app.processors.embedding import EmbeddingProvider, OpenAICompatibleEmbeddingProvider
from app.schemas.search import (SearchHit, SearchMatchResponse, SearchNoteBrief,
    SearchNoteResult, SearchPageResponse, SearchPaperBrief, SearchPaperResult,
    SearchRetrievalMetadata)
from app.services.hybrid_search import materialize_fusion
from app.services.search_providers import (ChunkSearchProvider, ElementSearchProvider,
    MetadataSearchProvider, NoteSearchProvider, ReferenceSearchProvider, SectionSearchProvider)
from app.services.search_query import QueryNormalizer
from app.services.semantic_search import (ChunkSemanticSearchProvider,
    NoteSemanticSearchProvider, SemanticQueryService)

SOURCE_WEIGHT = {"title": 1.0, "doi": 1.0, "arxiv": 1.0, "author": 0.85, "keyword": 0.85,
    "tag": 0.8, "abstract": 0.75, "section": 0.75, "journal": 0.7, "conference": 0.7,
    "publisher": 0.65, "chunk": 0.6, "reference": 0.45, "figure": 0.4, "table": 0.4,
    "note_title": 1.0, "note_content": 0.75, "research_background": 0.75,
    "research_problem": 0.85, "research_method": 0.75, "research_contribution": 0.85,
    "research_experiment": 0.75, "research_conclusion": 0.7, "research_thought": 0.7}
MAX_MATCHES = 5


class SearchAggregator:
    @staticmethod
    def fingerprint(hit: SearchHit) -> str:
        value = hit.snippet or hit.text
        return re.sub(r"\s+", " ", value).strip().casefold()[:500]

    def aggregate(self, hits: list[SearchHit], id_field: str, *, semantic: bool = False) -> dict[uuid.UUID, tuple[float, int, list[SearchHit]]]:
        grouped: dict[uuid.UUID, list[SearchHit]] = defaultdict(list)
        for hit in hits:
            entity_id = getattr(hit, id_field)
            if entity_id is not None:
                grouped[entity_id].append(hit)
        output = {}
        for paper_id, paper_hits in grouped.items():
            sources = {hit.source for hit in paper_hits}
            weighted = [((1.0 if semantic else SOURCE_WEIGHT[hit.source]) * hit.raw_score, hit) for hit in paper_hits]
            best_score = max(score for score, _ in weighted)
            score = best_score + (0.02 * min(len(paper_hits) - 1, 3) if semantic
                else 0.08 * min(len(sources) - 1, 3) + 0.02 * min(len(paper_hits) - 1, 5))
            ranked = [hit for _, hit in sorted(weighted, key=lambda pair: (
                -pair[0], -SOURCE_WEIGHT[pair[1].source], pair[1].page_start is None,
                pair[1].page_start or 0, pair[1].source, pair[1].text,
            ))]
            seen: set[str] = set()
            selected = []
            for hit in ranked:
                fingerprint = self.fingerprint(hit)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                selected.append(hit)
                if len(selected) == MAX_MATCHES:
                    break
            output[paper_id] = (score, len(paper_hits), selected)
        return output


class SearchService:
    def __init__(self, db: AsyncSession, embedding_provider: EmbeddingProvider | None = None):
        self.db = db
        self.providers = [MetadataSearchProvider(), SectionSearchProvider(), ChunkSearchProvider(), ReferenceSearchProvider(), ElementSearchProvider()]
        self.note_provider = NoteSearchProvider()
        self.aggregator = SearchAggregator()
        self.embedding_provider = embedding_provider

    async def search(self, user_id: uuid.UUID, query: str, page: int = 1, page_size: int = 20,
                     mode: str = "lexical") -> SearchPageResponse:
        if mode == "hybrid":
            return await self._search_hybrid(user_id, query, page, page_size)
        normalized = QueryNormalizer.normalize(query)
        if len(normalized.normalized) < 2:
            return SearchPageResponse(items=[], total=0, page=page, page_size=page_size)
        semantic = mode == "semantic"
        if semantic:
            provider = self.embedding_provider or OpenAICompatibleEmbeddingProvider()
            normalized_query, vector = await SemanticQueryService(provider).embed_query(query)
            hits = await ChunkSemanticSearchProvider().search(self.db, user_id, normalized_query, vector, provider)
            note_hits = await NoteSemanticSearchProvider().search(self.db, user_id, normalized_query, vector, provider)
        else:
            hits = []
            # Keep the native `%` operator indexable while allowing useful partial
            # academic-title typos. The setting is transaction-local.
            await self.db.execute(select(func.set_config("pg_trgm.similarity_threshold", "0.2", True)))
            providers = ([self.providers[0], self.providers[3]]
                if normalized.looks_like_doi or normalized.looks_like_arxiv else self.providers)
            for provider in providers:
                hits.extend(await provider.search(self.db, user_id, normalized))
            note_hits = await self.note_provider.search(self.db, user_id, normalized)
        paper_aggregated = self.aggregator.aggregate(hits, "paper_id", semantic=semantic)
        note_aggregated = self.aggregator.aggregate(note_hits, "note_id", semantic=semantic)
        if not paper_aggregated and not note_aggregated:
            return SearchPageResponse(items=[], total=0, page=page, page_size=page_size)
        papers = (await self.db.execute(
            select(Paper).where(Paper.user_id == user_id, Paper.id.in_(paper_aggregated)).options(selectinload(Paper.authors).selectinload(PaperAuthor.author))
        )).scalars().all()
        paper_map = {paper.id: paper for paper in papers}
        notes = (await self.db.execute(select(Note).where(
            Note.user_id == user_id, Note.id.in_(note_aggregated)
        ))).scalars().all()
        note_map = {note.id: note for note in notes}
        paper_titles = {paper.id: paper.title for paper in (await self.db.execute(select(Paper).where(
            Paper.user_id == user_id, Paper.id.in_({n.paper_id for n in notes if n.paper_id})
        ))).scalars().all()}

        entities = [("paper", eid, data[0], paper_map[eid].updated_at) for eid, data in paper_aggregated.items() if eid in paper_map]
        entities += [("note", eid, data[0], note_map[eid].updated_at) for eid, data in note_aggregated.items() if eid in note_map]
        entities.sort(key=lambda item: (-item[2], -item[3].timestamp(), item[0], str(item[1])))
        total = len(entities)
        page_entities = entities[(page - 1) * page_size: page * page_size]
        items: list[SearchPaperResult | SearchNoteResult] = []
        for entity_type, entity_id, _, _ in page_entities:
            aggregated = paper_aggregated if entity_type == "paper" else note_aggregated
            if entity_type == "note":
                note = note_map[entity_id]
                score, match_count, matches = aggregated[entity_id]
                items.append(SearchNoteResult(note=SearchNoteBrief(id=note.id, title=note.title,
                    note_type=note.note_type, paper_id=note.paper_id,
                    paper_title=paper_titles.get(note.paper_id)), score=score, match_count=match_count,
                    matches=[SearchMatchResponse(**hit.model_dump(exclude={"entity_type", "paper_id", "note_id", "raw_score", "match_type", "retrieval_method"})) for hit in matches]))
                continue
            paper_id = entity_id
            paper = paper_map[paper_id]
            score, match_count, matches = aggregated[paper_id]
            authors = [assignment.author.name for assignment in sorted(paper.authors, key=lambda item: item.author_order)]
            items.append(SearchPaperResult(paper=SearchPaperBrief(id=paper.id, title=paper.title, publication_year=paper.publication_year, authors=authors), score=score, match_count=match_count, matches=[SearchMatchResponse(**hit.model_dump(exclude={"entity_type", "paper_id", "note_id", "raw_score", "match_type", "retrieval_method"})) for hit in matches]))
        return SearchPageResponse(items=items, total=total, page=page, page_size=page_size)

    async def _semantic_index_ready(self, user_id: uuid.UUID, provider: EmbeddingProvider) -> bool:
        chunk_ready = await self.db.scalar(select(func.count()).select_from(Chunk)
            .join(Document, Document.id == Chunk.document_id).join(Paper, Paper.id == Document.paper_id)
            .where(Paper.user_id == user_id, Chunk.embedding_status == "ready",
                Chunk.embedding_model == provider.model_name,
                Chunk.embedding_dimension == provider.dimension, Chunk.embedding.is_not(None)))
        if chunk_ready:
            return True
        note_ready = await self.db.scalar(select(func.count()).select_from(Note).where(
            Note.user_id == user_id, Note.embedding_status == "ready",
            Note.embedding_model == provider.model_name,
            Note.embedding_dimension == provider.dimension, Note.embedding.is_not(None)))
        return bool(note_ready)

    async def _search_hybrid(self, user_id: uuid.UUID, query: str, page: int,
                             page_size: int) -> SearchPageResponse:
        candidate_size = min(settings.HYBRID_MAX_CANDIDATE_ENTITIES,
            max(settings.HYBRID_CANDIDATE_ENTITIES, page * page_size * 3))
        lexical = await self.search(user_id, query, 1, candidate_size, "lexical")
        provider = self.embedding_provider or OpenAICompatibleEmbeddingProvider()
        index_ready = await self._semantic_index_ready(user_id, provider)
        try:
            semantic = await self.search(user_id, query, 1, candidate_size, "semantic")
        except SemanticRetrievalError:
            start = (page - 1) * page_size
            return SearchPageResponse(items=lexical.items[start:start + page_size], total=lexical.total,
                page=page, page_size=page_size, retrieval=SearchRetrievalMetadata(
                    requested_mode="hybrid", effective_mode="lexical", semantic_available=False,
                    semantic_index_ready=index_ready))
        fused = materialize_fusion(lexical.items, semantic.items)
        start = (page - 1) * page_size
        effective = "hybrid" if index_ready else "lexical"
        return SearchPageResponse(items=fused[start:start + page_size], total=len(fused),
            page=page, page_size=page_size, retrieval=SearchRetrievalMetadata(
                requested_mode="hybrid", effective_mode=effective, semantic_available=True,
                semantic_index_ready=index_ready))
