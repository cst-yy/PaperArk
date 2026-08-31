import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import PaperNotFoundError
from app.models import ManualMindMapEdge, ManualMindMapNode, Note, Paper, ResearchContribution, ResearchExperiment, ResearchNoteProfile
from app.schemas.mind_map import ManualMindMapEdgeCreate, ManualMindMapEdgeUpdate, ManualMindMapNodeCreate, ManualMindMapNodeUpdate, MindMapEdge, MindMapNode, MindMapResponse


class MindMapService:
    FIELDS = (("research_problem", "Research Problem"), ("method_summary", "Method"),
        ("results_summary", "Results"), ("conclusion", "Conclusion"),
        ("limitations", "Limitations"), ("future_work", "Future Work"))

    def __init__(self, db: AsyncSession): self.db = db

    async def get(self, user_id: uuid.UUID, paper_id: uuid.UUID):
        paper = await self.db.scalar(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
        if paper is None: raise PaperNotFoundError("Paper not found")
        root = MindMapNode(id=f"paper:{paper.id}", node_type="paper", title=paper.title, paper_id=paper.id)
        manual_rows = list((await self.db.scalars(select(ManualMindMapNode).where(ManualMindMapNode.user_id == user_id, ManualMindMapNode.paper_id == paper_id).order_by(ManualMindMapNode.created_at))).all())
        manual_edges = list((await self.db.scalars(select(ManualMindMapEdge).where(ManualMindMapEdge.user_id == user_id, ManualMindMapEdge.paper_id == paper_id).order_by(ManualMindMapEdge.created_at))).all())
        authored_nodes = [MindMapNode(id=f"manual:{item.id}", node_type="manual", title=item.title, summary=item.summary, paper_id=paper.id, entity_id=item.id) for item in manual_rows]
        authored_edges = [MindMapEdge(id=item.id, source=item.source_key, target=item.target_key, relation=item.relation, manual=True) for item in manual_edges]
        profile = await self.db.scalar(select(ResearchNoteProfile).join(Note).where(
            Note.user_id == user_id, Note.paper_id == paper_id, Note.note_type == "research")
            .options(selectinload(ResearchNoteProfile.contributions).selectinload(ResearchContribution.evidence_links),
                selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.evidence_links),
                selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.contribution_links))
            .order_by(ResearchNoteProfile.updated_at.desc()).limit(1))
        if profile is None:
            return MindMapResponse(paper_id=paper.id, nodes=[root, *authored_nodes], edges=authored_edges, has_profile=False)
        nodes, edges = [root], []
        for field, title in self.FIELDS:
            value = getattr(profile, field)
            if value.strip():
                node_id = f"field:{field}"
                nodes.append(MindMapNode(id=node_id, node_type="profile_field", title=title,
                    summary=value, paper_id=paper.id, note_id=profile.note_id))
                edges.append(MindMapEdge(source=root.id, target=node_id, relation="contains"))
        contribution_ids = set()
        for item in profile.contributions:
            node_id = f"contribution:{item.id}"; contribution_ids.add(item.id)
            summary = "\n".join(value for value in (
                f"Problem: {item.problem}" if item.problem else "",
                f"Prior Limitation: {item.prior_limitation}" if item.prior_limitation else "",
                f"Innovation: {item.innovation}" if item.innovation else "",
                f"Solution: {item.solution}" if item.solution else "",
                f"Evidence Summary: {item.evidence_summary}" if item.evidence_summary else "",
            ) if value)
            nodes.append(MindMapNode(id=node_id, node_type="contribution",
                title=f"Contribution {item.order_index + 1}", summary=summary, paper_id=paper.id,
                note_id=profile.note_id, entity_id=item.id,
                evidence_ids=[link.note_evidence_id for link in item.evidence_links]))
            edges.append(MindMapEdge(source=root.id, target=node_id, relation="contains"))
        for item in profile.experiments:
            node_id = f"experiment:{item.id}"
            summary = "\n".join(value for value in (
                f"Task: {item.task}" if item.task else "",
                f"Datasets: {', '.join(item.datasets_json)}" if item.datasets_json else "",
                f"Baselines: {', '.join(item.baselines_json)}" if item.baselines_json else "",
                f"Metrics: {', '.join(item.metrics_json)}" if item.metrics_json else "",
                f"Result: {item.result}" if item.result else "",
                f"Conclusion: {item.conclusion}" if item.conclusion else "",
            ) if value)
            nodes.append(MindMapNode(id=node_id, node_type="experiment",
                title=item.task or f"Experiment {item.order_index + 1}",
                summary=summary, paper_id=paper.id, note_id=profile.note_id,
                entity_id=item.id, evidence_ids=[link.note_evidence_id for link in item.evidence_links]))
            parents = [link.contribution_id for link in item.contribution_links if link.contribution_id in contribution_ids]
            if parents:
                edges.extend(MindMapEdge(source=f"contribution:{value}", target=node_id, relation="supports") for value in parents)
            else: edges.append(MindMapEdge(source=root.id, target=node_id, relation="contains"))
        return MindMapResponse(paper_id=paper.id, note_id=profile.note_id, profile_revision=profile.revision,
            nodes=[*nodes, *authored_nodes], edges=[*edges, *authored_edges], has_profile=True)

    async def create_node(self, user_id: uuid.UUID, paper_id: uuid.UUID, data: ManualMindMapNodeCreate):
        await self._paper(user_id, paper_id)
        self.db.add(ManualMindMapNode(user_id=user_id, paper_id=paper_id, title=data.title.strip(), summary=data.summary.strip()))
        await self.db.flush()

    async def update_node(self, user_id: uuid.UUID, paper_id: uuid.UUID, node_id: uuid.UUID, data: ManualMindMapNodeUpdate):
        row = await self._node(user_id, paper_id, node_id); row.title = data.title.strip(); row.summary = data.summary.strip(); await self.db.flush()

    async def delete_node(self, user_id: uuid.UUID, paper_id: uuid.UUID, node_id: uuid.UUID):
        row = await self._node(user_id, paper_id, node_id); key = f"manual:{row.id}"
        edges = list((await self.db.scalars(select(ManualMindMapEdge).where(ManualMindMapEdge.user_id == user_id, ManualMindMapEdge.paper_id == paper_id, or_(ManualMindMapEdge.source_key == key, ManualMindMapEdge.target_key == key)))).all())
        for edge in edges: await self.db.delete(edge)
        await self.db.delete(row); await self.db.flush()

    async def create_edge(self, user_id: uuid.UUID, paper_id: uuid.UUID, data: ManualMindMapEdgeCreate):
        graph = await self.get(user_id, paper_id); keys = {node.id for node in graph.nodes}
        if data.source not in keys or data.target not in keys or data.source == data.target: raise ValueError("Invalid mind map endpoints")
        self.db.add(ManualMindMapEdge(user_id=user_id, paper_id=paper_id, source_key=data.source, target_key=data.target, relation=data.relation.strip())); await self.db.flush()

    async def update_edge(self, user_id: uuid.UUID, paper_id: uuid.UUID, edge_id: uuid.UUID, data: ManualMindMapEdgeUpdate):
        row = await self._edge(user_id, paper_id, edge_id); row.relation = data.relation.strip(); await self.db.flush()

    async def delete_edge(self, user_id: uuid.UUID, paper_id: uuid.UUID, edge_id: uuid.UUID):
        row = await self._edge(user_id, paper_id, edge_id); await self.db.delete(row); await self.db.flush()

    async def _paper(self, user_id, paper_id):
        paper = await self.db.scalar(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
        if paper is None: raise PaperNotFoundError("Paper not found")
        return paper

    async def _node(self, user_id, paper_id, node_id):
        row = await self.db.scalar(select(ManualMindMapNode).where(ManualMindMapNode.id == node_id, ManualMindMapNode.user_id == user_id, ManualMindMapNode.paper_id == paper_id))
        if row is None: raise LookupError("Mind map node not found")
        return row

    async def _edge(self, user_id, paper_id, edge_id):
        row = await self.db.scalar(select(ManualMindMapEdge).where(ManualMindMapEdge.id == edge_id, ManualMindMapEdge.user_id == user_id, ManualMindMapEdge.paper_id == paper_id))
        if row is None: raise LookupError("Mind map edge not found")
        return row
