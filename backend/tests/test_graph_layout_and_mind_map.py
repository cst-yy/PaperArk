import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.models import Note, Paper, User
from app.schemas.graph_layout import GraphLayoutSave, NodePosition
from app.schemas.mind_map import ManualMindMapEdgeCreate, ManualMindMapEdgeUpdate, ManualMindMapNodeCreate, ManualMindMapNodeUpdate
from app.schemas.research_note import ContributionInput, ExperimentInput, ResearchProfileAggregate
from app.services.graph_layout_service import GraphLayoutService
from app.services.mind_map_service import MindMapService
from app.services.research_note_service import ResearchNoteService


async def make_user(db, name):
    value = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    db.add(value); await db.flush(); return value


async def make_paper(db, owner, title):
    value = Paper(user_id=owner.id, title=title, status="ready")
    db.add(value); await db.flush(); return value


@pytest.mark.asyncio
async def test_layout_is_user_scoped_replaced_and_separate_from_graph_data(session: AsyncSession):
    owner, foreign = await make_user(session, "layout-owner"), await make_user(session, "layout-foreign")
    service = GraphLayoutService(session)
    saved = await service.save(owner.id, GraphLayoutSave(graph_type="knowledge", scope_key="paper:a:depth:2",
        positions={"a": NodePosition(x=10, y=20), "b": NodePosition(x=30, y=40)}))
    assert saved.positions["a"].x == 10
    assert await service.get(foreign.id, "knowledge", "paper:a:depth:2") is None
    replaced = await service.save(owner.id, GraphLayoutSave(graph_type="knowledge", scope_key="paper:a:depth:2",
        positions={"a": NodePosition(x=90, y=80)}))
    assert replaced.id == saved.id and set(replaced.positions) == {"a"}


@pytest.mark.asyncio
async def test_mind_map_is_profile_derived_and_tracks_profile_updates(session: AsyncSession):
    owner, foreign = await make_user(session, "mind-owner"), await make_user(session, "mind-foreign")
    paper = await make_paper(session, owner, "Graph Paper")
    note = Note(user_id=owner.id, paper_id=paper.id, title="Research", note_type="research")
    session.add(note); await session.flush()
    service = MindMapService(session)
    empty = await service.get(owner.id, paper.id)
    assert empty.has_profile is False and len(empty.nodes) == 1
    with pytest.raises(PaperNotFoundError): await service.get(foreign.id, paper.id)

    first = ResearchProfileAggregate(research_problem="Problem", method_summary="Method",
        contributions=[ContributionInput(client_id="c1", innovation="New idea")],
        experiments=[ExperimentInput(client_id="e1", task="Benchmark", result="Wins",
            supports_contribution_client_ids=["c1"])])
    await ResearchNoteService(session).save(owner.id, note.id, first)
    graph = await service.get(owner.id, paper.id)
    assert graph.has_profile and {node.node_type for node in graph.nodes} == {
        "paper", "profile_field", "contribution", "experiment"}
    contribution = next(node for node in graph.nodes if node.node_type == "contribution")
    experiment = next(node for node in graph.nodes if node.node_type == "experiment")
    assert any(edge.source == contribution.id and edge.target == experiment.id and edge.relation == "supports"
        for edge in graph.edges)

    second = ResearchProfileAggregate(research_problem="Updated problem")
    await ResearchNoteService(session).save(owner.id, note.id, second)
    updated = await service.get(owner.id, paper.id)
    assert updated.profile_revision == graph.profile_revision + 1
    assert not any(node.node_type in {"contribution", "experiment"} for node in updated.nodes)
    assert next(node for node in updated.nodes if node.node_type == "profile_field").summary == "Updated problem"


@pytest.mark.asyncio
async def test_manual_mind_map_crud_persists_and_is_user_scoped(session: AsyncSession):
    owner, foreign = await make_user(session, "manual-map-owner"), await make_user(session, "manual-map-foreign")
    paper = await make_paper(session, owner, "Manual map")
    service = MindMapService(session)

    await service.create_node(owner.id, paper.id, ManualMindMapNodeCreate(title="Hypothesis", summary="Initial"))
    graph = await service.get(owner.id, paper.id)
    manual = next(node for node in graph.nodes if node.node_type == "manual")
    assert manual.summary == "Initial" and graph.has_profile is False

    await service.update_node(owner.id, paper.id, manual.entity_id,
        ManualMindMapNodeUpdate(title="Updated hypothesis", summary="Persistent"))
    await service.create_edge(owner.id, paper.id, ManualMindMapEdgeCreate(
        source=f"paper:{paper.id}", target=manual.id, relation="explains"))
    graph = await service.get(owner.id, paper.id)
    edge = next(item for item in graph.edges if item.manual)
    assert next(node for node in graph.nodes if node.id == manual.id).title == "Updated hypothesis"
    assert edge.relation == "explains"

    await service.update_edge(owner.id, paper.id, edge.id, ManualMindMapEdgeUpdate(relation="supports"))
    assert next(item for item in (await service.get(owner.id, paper.id)).edges if item.manual).relation == "supports"
    with pytest.raises(PaperNotFoundError):
        await service.get(foreign.id, paper.id)

    await service.delete_node(owner.id, paper.id, manual.entity_id)
    deleted = await service.get(owner.id, paper.id)
    assert all(node.node_type != "manual" for node in deleted.nodes)
    assert all(not item.manual for item in deleted.edges)
