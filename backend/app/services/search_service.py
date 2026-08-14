"""Paper-level search aggregation for the stable S8-A contract."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Paper, PaperAuthor
from app.schemas.search import SearchHit, SearchMatchResponse, SearchPageResponse, SearchPaperBrief, SearchPaperResult
from app.services.search_providers import ChunkSearchProvider, ElementSearchProvider, MetadataSearchProvider, ReferenceSearchProvider, SectionSearchProvider
from app.services.search_query import QueryNormalizer

SOURCE_WEIGHT = {"title": 1.0, "doi": 1.0, "arxiv": 1.0, "author": 0.85, "keyword": 0.85,
    "tag": 0.8, "abstract": 0.75, "section": 0.75, "journal": 0.7, "conference": 0.7,
    "publisher": 0.65, "chunk": 0.6, "reference": 0.45, "figure": 0.4, "table": 0.4}
MAX_MATCHES = 5


class SearchAggregator:
    @staticmethod
    def fingerprint(hit: SearchHit) -> str:
        value = hit.snippet or hit.text
        return re.sub(r"\s+", " ", value).strip().casefold()[:500]

    def aggregate(self, hits: list[SearchHit]) -> dict[uuid.UUID, tuple[float, int, list[SearchHit]]]:
        grouped: dict[uuid.UUID, list[SearchHit]] = defaultdict(list)
        for hit in hits:
            grouped[hit.paper_id].append(hit)
        output = {}
        for paper_id, paper_hits in grouped.items():
            sources = {hit.source for hit in paper_hits}
            weighted = [(SOURCE_WEIGHT[hit.source] * hit.raw_score, hit) for hit in paper_hits]
            best_score = max(score for score, _ in weighted)
            score = best_score + 0.08 * min(len(sources) - 1, 3) + 0.02 * min(len(paper_hits) - 1, 5)
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
    def __init__(self, db: AsyncSession):
        self.db = db
        self.providers = [MetadataSearchProvider(), SectionSearchProvider(), ChunkSearchProvider(), ReferenceSearchProvider(), ElementSearchProvider()]
        self.aggregator = SearchAggregator()

    async def search(self, user_id: uuid.UUID, query: str, page: int = 1, page_size: int = 20) -> SearchPageResponse:
        normalized = QueryNormalizer.normalize(query)
        if len(normalized.normalized) < 2:
            return SearchPageResponse(items=[], total=0, page=page, page_size=page_size)
        hits: list[SearchHit] = []
        # Keep the native `%` operator indexable while allowing useful partial
        # academic-title typos. The setting is transaction-local.
        await self.db.execute(select(func.set_config("pg_trgm.similarity_threshold", "0.2", True)))
        providers = ([self.providers[0], self.providers[3]]
            if normalized.looks_like_doi or normalized.looks_like_arxiv else self.providers)
        for provider in providers:
            hits.extend(await provider.search(self.db, user_id, normalized))
        aggregated = self.aggregator.aggregate(hits)
        if not aggregated:
            return SearchPageResponse(items=[], total=0, page=page, page_size=page_size)
        papers = (await self.db.execute(
            select(Paper).where(Paper.user_id == user_id, Paper.id.in_(aggregated)).options(selectinload(Paper.authors).selectinload(PaperAuthor.author))
        )).scalars().all()
        paper_map = {paper.id: paper for paper in papers}
        ranked_ids = sorted((paper_id for paper_id in aggregated if paper_id in paper_map), key=lambda paper_id: (
            -aggregated[paper_id][0],
            -max(SOURCE_WEIGHT[hit.source] for hit in aggregated[paper_id][2]),
            -paper_map[paper_id].updated_at.timestamp(),
            str(paper_id),
        ))
        total = len(ranked_ids)
        page_ids = ranked_ids[(page - 1) * page_size: page * page_size]
        items = []
        for paper_id in page_ids:
            paper = paper_map[paper_id]
            score, match_count, matches = aggregated[paper_id]
            authors = [assignment.author.name for assignment in sorted(paper.authors, key=lambda item: item.author_order)]
            items.append(SearchPaperResult(paper=SearchPaperBrief(id=paper.id, title=paper.title, publication_year=paper.publication_year, authors=authors), score=score, match_count=match_count, matches=[SearchMatchResponse(**hit.model_dump(exclude={"paper_id", "raw_score", "match_type"})) for hit in matches]))
        return SearchPageResponse(items=items, total=total, page=page, page_size=page_size)
