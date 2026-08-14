"""Search providers backed by short-text trigram matching and PostgreSQL FTS."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Author, Chunk, Document, DocumentElement, Keyword, Paper, PaperAuthor,
    PaperKeyword, PaperTag, Reference, Section, Tag,
)
from app.schemas.search import SearchHit, SearchMatchType
from app.services.search_query import NormalizedSearchQuery, build_snippet

def _metadata_quality(value: str, query: NormalizedSearchQuery, similarity: float) -> tuple[SearchMatchType, float]:
    folded = " ".join(value.split()).casefold()
    if folded == query.normalized:
        return "exact", 1.0
    if folded.startswith(query.normalized):
        return "prefix", 0.9
    return "fuzzy", max(0.0, min(float(similarity), 1.0))


def _fts_score(rank: float) -> float:
    rank = max(float(rank), 0.0)
    return min(rank / (rank + 0.1), 1.0) if rank else 0.0


def _short_text_predicate(column: Any, query: NormalizedSearchQuery) -> Any:
    return or_(column.ilike(f"%{query.normalized}%"), column.op("%") (query.normalized))


class MetadataSearchProvider:
    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[SearchHit]:
        if query.looks_like_doi or query.looks_like_arxiv:
            source, column = ("doi", Paper.doi) if query.looks_like_doi else ("arxiv", Paper.arxiv_id)
            rows = (await db.execute(select(Paper.id, column).where(
                Paper.user_id == user_id, func.lower(column) == query.normalized
            ))).all()
            return [SearchHit(paper_id=paper_id, source=source, text=value, snippet=value,
                raw_score=1.0, match_type="exact") for paper_id, value in rows]

        hits: list[SearchHit] = []
        short_fields = (
            ("title", Paper.title), ("journal", Paper.journal),
            ("conference", Paper.conference), ("publisher", Paper.publisher),
        )
        for source, column in short_fields:
            similarity = func.similarity(column, query.normalized)
            rows = (await db.execute(select(Paper.id, column, similarity).where(
                Paper.user_id == user_id, column.is_not(None), _short_text_predicate(column, query)
            ))).all()
            for paper_id, value, score in rows:
                match_type, raw_score = _metadata_quality(value, query, score)
                hits.append(SearchHit(paper_id=paper_id, source=source, text=value,
                    snippet=build_snippet(value, query), raw_score=raw_score, match_type=match_type))

        rows = (await db.execute(select(Paper.id, Paper.abstract).where(
            Paper.user_id == user_id, Paper.abstract.ilike(f"%{query.normalized}%")
        ))).all()
        hits.extend(SearchHit(paper_id=paper_id, source="abstract", text=value,
            snippet=build_snippet(value, query), raw_score=0.7, match_type="fulltext") for paper_id, value in rows)

        relation_specs = (
            ("author", Author, Author.name, PaperAuthor, PaperAuthor.author_id, Author.id),
            ("tag", Tag, Tag.name, PaperTag, PaperTag.tag_id, Tag.id),
            ("keyword", Keyword, Keyword.display_name, PaperKeyword, PaperKeyword.keyword_id, Keyword.id),
        )
        for source, model, column, link, left, right in relation_specs:
            similarity = func.similarity(column, query.normalized)
            rows = (await db.execute(select(link.paper_id, column, similarity)
                .join(model, left == right).join(Paper, Paper.id == link.paper_id)
                .where(Paper.user_id == user_id, _short_text_predicate(column, query)))).all()
            for paper_id, value, score in rows:
                match_type, raw_score = _metadata_quality(value, query, score)
                hits.append(SearchHit(paper_id=paper_id, source=source, text=value, snippet=value,
                    raw_score=raw_score, match_type=match_type))
        return hits


class _FullTextProvider:
    model: Any

    def fallback_predicate(self, pattern: str) -> Any:
        raise NotImplementedError

    async def rows(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[Any]:
        tsquery = func.websearch_to_tsquery("simple", query.normalized)
        vector = getattr(self.model, "search_vector")
        rank = func.ts_rank_cd(vector, tsquery)
        rows = (await db.execute(select(self.model, Document.paper_id, rank)
            .join(Document, Document.id == self.model.document_id)
            .join(Paper, Paper.id == Document.paper_id)
            .where(Paper.user_id == user_id, vector.op("@@")(tsquery))
            .order_by(rank.desc()))).all()
        if rows:
            return [(item, paper_id, _fts_score(rank)) for item, paper_id, rank in rows]
        # PostgreSQL tokenization can miss long camel-case/model identifiers that
        # legacy substring search found. Keep a narrow, single-token fallback.
        if len(query.tokens) == 1 and len(query.normalized) >= 12:
            fallback = (await db.execute(select(self.model, Document.paper_id)
                .join(Document, Document.id == self.model.document_id)
                .join(Paper, Paper.id == Document.paper_id)
                .where(Paper.user_id == user_id, self.fallback_predicate(f"%{query.normalized}%")))).all()
            return [(item, paper_id, 0.55) for item, paper_id in fallback]
        return []


class SectionSearchProvider(_FullTextProvider):
    model = Section

    def fallback_predicate(self, pattern: str) -> Any:
        return or_(Section.title.ilike(pattern), Section.content.ilike(pattern))

    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[SearchHit]:
        return [SearchHit(paper_id=paper_id, document_id=item.document_id, source="section",
            text=item.title, snippet=build_snippet(item.content or item.title, query),
            page_start=item.page_start, page_end=item.page_end, section_id=item.id,
            raw_score=rank, match_type="fulltext") for item, paper_id, rank in await self.rows(db, user_id, query)]


class ChunkSearchProvider(_FullTextProvider):
    model = Chunk

    def fallback_predicate(self, pattern: str) -> Any:
        return Chunk.content.ilike(pattern)

    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[SearchHit]:
        return [SearchHit(paper_id=paper_id, document_id=item.document_id, source="chunk",
            text=item.content, snippet=build_snippet(item.content, query),
            page_start=item.page_start or item.page_number, page_end=item.page_end or item.page_number,
            section_id=item.section_id, raw_score=rank, match_type="fulltext")
            for item, paper_id, rank in await self.rows(db, user_id, query)]


class ReferenceSearchProvider(_FullTextProvider):
    model = Reference

    def fallback_predicate(self, pattern: str) -> Any:
        return or_(Reference.title.ilike(pattern), Reference.raw_text.ilike(pattern))

    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[SearchHit]:
        if query.looks_like_doi or query.looks_like_arxiv:
            column = Reference.doi if query.looks_like_doi else Reference.arxiv_id
            rows = (await db.execute(select(Reference, Document.paper_id)
                .join(Document, Document.id == Reference.document_id).join(Paper, Paper.id == Document.paper_id)
                .where(Paper.user_id == user_id, func.lower(column) == query.normalized))).all()
            return [self._hit(item, paper_id, query, 1.0, "exact") for item, paper_id in rows]
        return [self._hit(item, paper_id, query, rank, "fulltext") for item, paper_id, rank in await self.rows(db, user_id, query)]

    @staticmethod
    def _hit(item: Reference, paper_id: uuid.UUID, query: NormalizedSearchQuery, score: float, match_type: SearchMatchType) -> SearchHit:
        return SearchHit(paper_id=paper_id, document_id=item.document_id, source="reference",
            text=item.title or item.raw_text, snippet=build_snippet(item.raw_text, query),
            page_start=item.page_start, page_end=item.page_end, section_id=item.section_id,
            raw_score=score, match_type=match_type)


class ElementSearchProvider(_FullTextProvider):
    model = DocumentElement

    def fallback_predicate(self, pattern: str) -> Any:
        return or_(DocumentElement.label.ilike(pattern), DocumentElement.caption.ilike(pattern))

    async def search(self, db: AsyncSession, user_id: uuid.UUID, query: NormalizedSearchQuery) -> list[SearchHit]:
        return [SearchHit(paper_id=paper_id, document_id=item.document_id, source=item.element_type,
            text=item.caption, snippet=build_snippet(item.caption, query), page_start=item.page_number,
            page_end=item.page_number, section_id=item.section_id, raw_score=rank,
            match_type="fulltext") for item, paper_id, rank in await self.rows(db, user_id, query)]
