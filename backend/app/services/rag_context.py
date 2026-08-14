from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, replace
from typing import Literal

from app.core.config import settings
from app.schemas.rag import RAGSource


@dataclass(frozen=True, slots=True)
class RAGCandidate:
    source_key: str
    source_type: Literal["paper_chunk", "note"]
    title: str
    content: str
    paper_id: uuid.UUID | None = None
    paper_title: str | None = None
    document_id: uuid.UUID | None = None
    note_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_index: int | None = None
    retrieval_method: Literal["lexical", "semantic", "hybrid"] = "lexical"
    retrieval_score: float = 0.0
    lexical_rank: int | None = None
    semantic_rank: int | None = None


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _words(text: str) -> set[str]:
    return set(re.findall(r"[\w\u4e00-\u9fff]+", text.casefold()))


def _overlap(left: str, right: str) -> float:
    a, b = _words(left), _words(right)
    return len(a & b) / max(1, min(len(a), len(b)))


def _merge_adjacent(candidates: list[RAGCandidate]) -> list[RAGCandidate]:
    output: list[RAGCandidate] = []
    for candidate in candidates:
        previous = output[-1] if output else None
        can_merge = (previous is not None and candidate.source_type == previous.source_type == "paper_chunk"
            and candidate.document_id == previous.document_id and candidate.section_id == previous.section_id
            and candidate.chunk_index is not None and previous.chunk_index is not None
            and candidate.chunk_index == previous.chunk_index + 1
            and estimate_tokens(previous.content + "\n" + candidate.content) <= settings.RAG_MAX_CHUNK_SOURCE_TOKENS)
        if can_merge:
            overlap = _words(previous.content) & _words(candidate.content)
            suffix = " ".join(word for word in candidate.content.split() if word.casefold() not in overlap)
            output[-1] = replace(previous,
                source_key=f"chunk_window:{previous.source_key.split(':', 1)[1]}:{candidate.source_key.split(':', 1)[1]}",
                content=(previous.content + "\n" + suffix).strip(), page_end=candidate.page_end or previous.page_end,
                retrieval_score=max(previous.retrieval_score, candidate.retrieval_score))
        else:
            output.append(candidate)
    return output


class RAGContextAssembler:
    def assemble(self, candidates: list[RAGCandidate], *, max_sources: int,
                 token_budget: int, paper_scope: bool = False) -> tuple[list[RAGSource], str, int, bool]:
        keyed: list[RAGCandidate] = []
        seen_keys = set()
        for candidate in candidates:
            if candidate.source_key in seen_keys:
                continue
            seen_keys.add(candidate.source_key)
            keyed.append(candidate)
        adjacent = _merge_adjacent(keyed)
        deduped: list[RAGCandidate] = []
        for candidate in adjacent:
            if any(candidate.document_id == item.document_id and candidate.section_id == item.section_id
                    and candidate.source_type == item.source_type == "paper_chunk"
                    and _overlap(candidate.content, item.content) > 0.75 for item in deduped):
                continue
            deduped.append(candidate)
        merged = deduped
        selected: list[RAGSource] = []
        total = 0
        note_count = 0
        per_paper: dict[uuid.UUID, int] = {}
        truncated_any = len(merged) > max_sources
        for candidate in merged:
            if len(selected) >= max_sources:
                break
            if candidate.source_type == "note" and note_count >= settings.RAG_MAX_NOTE_SOURCES:
                continue
            if not paper_scope and candidate.source_type == "paper_chunk" and candidate.paper_id:
                if per_paper.get(candidate.paper_id, 0) >= settings.RAG_MAX_PAPER_SOURCES_PER_PAPER:
                    continue
            cap = settings.RAG_MAX_NOTE_SOURCE_TOKENS if candidate.source_type == "note" else settings.RAG_MAX_CHUNK_SOURCE_TOKENS
            content = candidate.content
            source_truncated = estimate_tokens(content) > cap
            if source_truncated:
                content = content[:cap * 4].rstrip()
            empty_source = RAGSource(source_key=candidate.source_key, source_type=candidate.source_type,
                paper_id=candidate.paper_id, paper_title=candidate.paper_title, document_id=candidate.document_id,
                note_id=candidate.note_id, section_id=candidate.section_id, section_title=candidate.section_title,
                page_start=candidate.page_start, page_end=candidate.page_end, title=candidate.title, content="",
                retrieval_method=candidate.retrieval_method, retrieval_score=candidate.retrieval_score,
                estimated_tokens=0)
            overhead = estimate_tokens(self.format_context([empty_source]))
            tokens = overhead + estimate_tokens(content)
            if total + tokens > token_budget:
                remaining = token_budget - total - overhead
                if remaining <= 0:
                    truncated_any = True
                    break
                content = content[:remaining * 4].rstrip()
                tokens = overhead + estimate_tokens(content)
                source_truncated = truncated_any = True
            source = RAGSource(source_key=candidate.source_key, source_type=candidate.source_type,
                paper_id=candidate.paper_id, paper_title=candidate.paper_title,
                document_id=candidate.document_id, note_id=candidate.note_id,
                section_id=candidate.section_id, section_title=candidate.section_title,
                page_start=candidate.page_start, page_end=candidate.page_end,
                title=candidate.title, content=content, retrieval_method=candidate.retrieval_method,
                retrieval_score=candidate.retrieval_score, estimated_tokens=tokens, truncated=source_truncated)
            selected.append(source)
            total += tokens
            if candidate.source_type == "note": note_count += 1
            elif candidate.paper_id: per_paper[candidate.paper_id] = per_paper.get(candidate.paper_id, 0) + 1
            if total >= token_budget:
                break
        return selected, self.format_context(selected), total, truncated_any or any(s.truncated for s in selected)

    @staticmethod
    def format_context(sources: list[RAGSource]) -> str:
        blocks = []
        for index, source in enumerate(sources, 1):
            if source.source_type == "paper_chunk":
                pages = str(source.page_start or "?") if source.page_start == source.page_end or source.page_end is None else f"{source.page_start or '?'}-{source.page_end}"
                header = f"[SOURCE {index} | PAPER]\nPaper: {source.paper_title or source.title}\nSection: {source.section_title or 'Unknown'}\nPages: {pages}"
            else:
                header = f"[SOURCE {index} | NOTE]\nNote: {source.title}"
            blocks.append(f"{header}\nContent:\n{source.content}")
        return "\n\n".join(blocks)
