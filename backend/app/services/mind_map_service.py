import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import PaperNotFoundError
from app.models import Note, Paper, ResearchContribution, ResearchExperiment, ResearchNoteProfile
from app.schemas.mind_map import MindMapEdge, MindMapNode, MindMapResponse


class MindMapService:
    FIELDS = (("research_problem", "Research Problem"), ("method_summary", "Method"),
        ("results_summary", "Results"), ("conclusion", "Conclusion"),
        ("limitations", "Limitations"), ("future_work", "Future Work"))

    def __init__(self, db: AsyncSession): self.db = db

    async def get(self, user_id: uuid.UUID, paper_id: uuid.UUID):
        paper = await self.db.scalar(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
        if paper is None: raise PaperNotFoundError("Paper not found")
        root = MindMapNode(id=f"paper:{paper.id}", node_type="paper", title=paper.title, paper_id=paper.id)
        profile = await self.db.scalar(select(ResearchNoteProfile).join(Note).where(
            Note.user_id == user_id, Note.paper_id == paper_id, Note.note_type == "research")
            .options(selectinload(ResearchNoteProfile.contributions).selectinload(ResearchContribution.evidence_links),
                selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.evidence_links),
                selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.contribution_links))
            .order_by(ResearchNoteProfile.updated_at.desc()).limit(1))
        if profile is None:
            return MindMapResponse(paper_id=paper.id, nodes=[root], edges=[], has_profile=False)
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
            nodes=nodes, edges=edges, has_profile=True)
