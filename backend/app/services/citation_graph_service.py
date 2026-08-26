from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.repositories.citation_graph_repository import CitationGraphRepository
from app.schemas.citation_graph import CitationEdgeDetail, CitationGraphEdge, CitationGraphNode, CitationGraphResponse


class CitationGraphService:
    def __init__(self, db: AsyncSession):
        self.repo = CitationGraphRepository(db)

    async def graph(
        self, user_id: uuid.UUID, *, paper_id: uuid.UUID | None,
        depth: int, limit_nodes: int,
    ) -> CitationGraphResponse:
        distances: dict[uuid.UUID, int] = {}
        if paper_id is not None:
            if not await self.repo.root_exists(user_id, paper_id):
                raise PaperNotFoundError("Paper not found")
            distances = {paper_id: 0}
            frontier = {paper_id}
            for level in range(1, depth + 1):
                edges = await self.repo.adjacent_edges(user_id, frontier)
                neighbors = {
                    value for edge in edges
                    for value in (edge.source_paper_id, edge.target_paper_id)
                    if value not in distances
                }
                for value in neighbors:
                    distances[value] = level
                frontier = neighbors
                if not frontier:
                    break
            candidate_ids = set(distances)
        else:
            candidate_ids, total_nodes = await self.repo.workspace_node_selection(
                user_id, limit_nodes
            )

        if paper_id is not None:
            total_nodes = len(candidate_ids)
        incoming, outgoing = await self.repo.degree_counts(user_id, candidate_ids)
        papers = await self.repo.papers(user_id, candidate_ids)
        paper_map = {paper.id: paper for paper in papers}

        def priority(value: uuid.UUID):
            paper = paper_map[value]
            degree = incoming.get(value, 0) + outgoing.get(value, 0)
            if paper_id is not None:
                return (distances[value], -degree, -paper.updated_at.timestamp(), str(value))
            return (-degree, -paper.updated_at.timestamp(), str(value))

        selected_ids = (
            set(sorted(paper_map, key=priority)[:limit_nodes])
            if paper_id is not None
            else set(paper_map)
        )
        # Root priority is distance zero, so it cannot be removed by truncation.
        selected_papers = sorted((paper_map[value] for value in selected_ids), key=lambda item: priority(item.id))
        edges = await self.repo.induced_edges(user_id, selected_ids)
        deduplicated = {edge.id: edge for edge in edges}
        return CitationGraphResponse(
            root_paper_id=paper_id, depth=depth,
            nodes=[CitationGraphNode(
                paper_id=paper.id, title=paper.title, publication_year=paper.publication_year,
                authors=[link.author.name for link in sorted(paper.authors, key=lambda link: link.author_order)],
                is_starred=paper.is_starred, reading_status=paper.reading_status,
                incoming_count=incoming.get(paper.id, 0), outgoing_count=outgoing.get(paper.id, 0),
            ) for paper in selected_papers],
            edges=[self._edge(edge) for edge in deduplicated.values()],
            truncated=len(selected_ids) < total_nodes, total_nodes=total_nodes,
        )

    async def edge_detail(self, user_id: uuid.UUID, relation_id: uuid.UUID) -> CitationEdgeDetail | None:
        result = await self.repo.edge_with_reference(user_id, relation_id)
        if result is None:
            return None
        relation, reference = result
        return CitationEdgeDetail(
            edge=self._edge(relation), raw_citation=reference.raw_text if reference else None,
            reference_order=reference.order_index if reference else None,
            match_method=reference.match_method if reference else None,
        )

    @staticmethod
    def _edge(relation) -> CitationGraphEdge:
        return CitationGraphEdge(
            relation_id=relation.id, source_paper_id=relation.source_paper_id,
            target_paper_id=relation.target_paper_id, relation_type="cites", origin="reference",
            confidence=relation.confidence, source_reference_id=relation.source_reference_id,
        )
