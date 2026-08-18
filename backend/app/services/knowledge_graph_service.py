from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from app.schemas.citation_graph import CitationGraphNode
from app.schemas.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphResponse


class KnowledgeGraphService:
    def __init__(self, db: AsyncSession, relation_types: set[str], origins: set[str]):
        self.repo = KnowledgeGraphRepository(db, relation_types, origins)

    async def graph(self, user_id: uuid.UUID, *, paper_id: uuid.UUID | None, depth: int, limit_nodes: int):
        distances: dict[uuid.UUID, int] = {}
        if paper_id is not None:
            if not await self.repo.root_exists(user_id, paper_id): raise PaperNotFoundError("Paper not found")
            distances, frontier = {paper_id: 0}, {paper_id}
            for level in range(1, depth + 1):
                edges = await self.repo.adjacent_edges(user_id, frontier)
                neighbors = {value for edge in edges for value in
                    (edge.source_paper_id, edge.target_paper_id) if value not in distances}
                distances.update({value: level for value in neighbors})
                frontier = neighbors
                if not frontier: break
            candidate_ids = set(distances)
        else:
            edges = await self.repo.workspace_edges(user_id)
            candidate_ids = {value for edge in edges for value in (edge.source_paper_id, edge.target_paper_id)}
        total_nodes = len(candidate_ids)
        incoming, outgoing = await self.repo.degree_counts(user_id, candidate_ids)
        paper_map = {paper.id: paper for paper in await self.repo.papers(user_id, candidate_ids)}
        def priority(value):
            paper, degree = paper_map[value], incoming.get(value, 0) + outgoing.get(value, 0)
            return ((distances[value], -degree) if paper_id else (-degree,)) + (-paper.updated_at.timestamp(), str(value))
        selected_ids = set(sorted(paper_map, key=priority)[:limit_nodes])
        relations = await self.repo.induced_edges(user_id, selected_ids)
        counts = await self.repo.evidence_counts({item.id for item in relations})
        papers = sorted((paper_map[value] for value in selected_ids), key=lambda item: priority(item.id))
        return KnowledgeGraphResponse(root_paper_id=paper_id, depth=depth,
            nodes=[CitationGraphNode(paper_id=paper.id, title=paper.title,
                publication_year=paper.publication_year,
                authors=[link.author.name for link in sorted(paper.authors, key=lambda link: link.author_order)],
                is_starred=paper.is_starred, reading_status=paper.reading_status,
                incoming_count=incoming.get(paper.id, 0), outgoing_count=outgoing.get(paper.id, 0)) for paper in papers],
            edges=[KnowledgeGraphEdge(relation_id=item.id, source_paper_id=item.source_paper_id,
                target_paper_id=item.target_paper_id, relation_type=item.relation_type, origin=item.origin,
                confidence=item.confidence, note=item.note, evidence_count=counts.get(item.id, 0)) for item in relations],
            truncated=len(selected_ids) < total_nodes, total_nodes=total_nodes)
