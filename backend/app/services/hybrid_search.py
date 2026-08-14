from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.core.config import settings
from app.schemas.search import SearchMatchResponse, SearchNoteResult, SearchPaperResult

SearchEntityResult = SearchPaperResult | SearchNoteResult
EntityKey = tuple[Literal["paper", "note"], UUID]


def entity_key(item: SearchEntityResult) -> EntityKey:
    return ("paper", item.paper.id) if item.entity_type == "paper" else ("note", item.note.id)


@dataclass(frozen=True, slots=True)
class HybridEntityScore:
    entity_key: EntityKey
    lexical_rank: int | None
    semantic_rank: int | None
    rrf_score: float


def rrf_fuse(lexical: list[SearchEntityResult], semantic: list[SearchEntityResult],
             k: int = settings.HYBRID_RRF_K) -> list[HybridEntityScore]:
    lexical_ranks = {entity_key(item): rank for rank, item in enumerate(lexical, 1)}
    semantic_ranks = {entity_key(item): rank for rank, item in enumerate(semantic, 1)}
    keys = lexical_ranks.keys() | semantic_ranks.keys()
    scores = [HybridEntityScore(key, lexical_ranks.get(key), semantic_ranks.get(key),
        (1 / (k + lexical_ranks[key]) if key in lexical_ranks else 0.0)
        + (1 / (k + semantic_ranks[key]) if key in semantic_ranks else 0.0)) for key in keys]
    return sorted(scores, key=lambda item: (-item.rrf_score,
        item.lexical_rank is None, item.lexical_rank or 10**9,
        item.semantic_rank is None, item.semantic_rank or 10**9,
        item.entity_key[0], str(item.entity_key[1])))


def _match_key(match: SearchMatchResponse) -> tuple:
    return (match.source, match.document_id, match.section_id, match.page_start,
        match.page_end, " ".join((match.text or match.snippet or "").split()).casefold()[:500])


def merge_entity_results(primary: SearchEntityResult, secondary: SearchEntityResult,
                         score: float, max_matches: int = 5) -> SearchEntityResult:
    seen = set()
    merged = []
    for match in [*primary.matches, *secondary.matches]:
        key = _match_key(match)
        if key not in seen:
            seen.add(key)
            merged.append(match)
    payload = primary.model_dump()
    payload.update(score=score, match_count=len(merged), matches=merged[:max_matches])
    return type(primary)(**payload)


def materialize_fusion(lexical: list[SearchEntityResult], semantic: list[SearchEntityResult]) -> list[SearchEntityResult]:
    lexical_map = {entity_key(item): item for item in lexical}
    semantic_map = {entity_key(item): item for item in semantic}
    output = []
    for fused in rrf_fuse(lexical, semantic):
        left, right = lexical_map.get(fused.entity_key), semantic_map.get(fused.entity_key)
        if left and right:
            output.append(merge_entity_results(left, right, fused.rrf_score))
        else:
            item = left or right
            payload = item.model_dump()
            payload["score"] = fused.rrf_score
            output.append(type(item)(**payload))
    return output
