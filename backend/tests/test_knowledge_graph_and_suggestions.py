import json
import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidPaperRelationError
from app.models import Paper, PaperRelation, PaperRelationSuggestion, User
from app.processors.generation import GenerationResult
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.knowledge_relation_service import KnowledgeRelationService
from app.services.relation_suggestion_service import RelationSuggestionService


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"
    async def generate(self, *args, **kwargs):
        return GenerationResult(text='{"relation_type":"none","confidence":0,"reason":"none","evidence_refs":[]}', model=self.model_name)


async def make_user(db, name):
    item = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    db.add(item); await db.flush(); return item


async def make_paper(db, user, title):
    item = Paper(user_id=user.id, title=title, status="ready")
    db.add(item); await db.flush(); return item


@pytest.mark.asyncio
async def test_suggestion_accept_reject_are_explicit_and_idempotent(session: AsyncSession):
    owner = await make_user(session, "suggest-owner")
    a, b, c = [await make_paper(session, owner, value) for value in "ABC"]
    first = PaperRelationSuggestion(user_id=owner.id, source_paper_id=a.id, target_paper_id=b.id,
        relation_type="extends", reason="grounded", evidence_json=[{"chunk_id": "x"}],
        provider_name="fake", model="fake")
    second = PaperRelationSuggestion(user_id=owner.id, source_paper_id=a.id, target_paper_id=c.id,
        relation_type="uses", reason="grounded", evidence_json=[], provider_name="fake", model="fake")
    session.add_all([first, second]); await session.flush()
    service = RelationSuggestionService(session, FakeProvider())
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 0
    accepted = await service.accept(owner.id, first.id)
    again = await service.accept(owner.id, first.id)
    assert accepted.accepted_relation_id == again.accepted_relation_id
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 1
    official = await KnowledgeRelationService(session).get(owner.id, accepted.accepted_relation_id)
    assert official.ai_evidence == [{"chunk_id": "x"}] and official.ai_provider_name == "fake"
    graph = await KnowledgeGraphService(session, {"extends"}, {"ai"}).graph(
        owner.id, paper_id=a.id, depth=1, limit_nodes=200)
    assert graph.edges[0].evidence_count == 1
    rejected = await service.reject(owner.id, second.id)
    assert rejected.status == "rejected"
    await service.reject(owner.id, second.id)
    assert await session.scalar(select(func.count()).select_from(PaperRelation)) == 1
    with pytest.raises(InvalidPaperRelationError): await service.accept(owner.id, second.id)
    with pytest.raises(InvalidPaperRelationError): RelationSuggestionService._parse(
        json.dumps({"relation_type": "related", "confidence": .8, "reason": "bad", "evidence_refs": []}))


@pytest.mark.asyncio
async def test_knowledge_graph_filters_bfs_cycles_induced_and_user_scope(session: AsyncSession):
    owner, foreign = await make_user(session, "kg-owner"), await make_user(session, "kg-foreign")
    a, b, c, d = [await make_paper(session, owner, value) for value in "ABCD"]
    x = await make_paper(session, foreign, "X")
    edges = [
        PaperRelation(user_id=owner.id, source_paper_id=a.id, target_paper_id=b.id, relation_type="extends", origin="manual"),
        PaperRelation(user_id=owner.id, source_paper_id=b.id, target_paper_id=c.id, relation_type="supports", origin="ai"),
        PaperRelation(user_id=owner.id, source_paper_id=c.id, target_paper_id=a.id, relation_type="uses", origin="manual"),
        PaperRelation(user_id=owner.id, source_paper_id=c.id, target_paper_id=d.id, relation_type="cites", origin="reference"),
        PaperRelation(user_id=owner.id, source_paper_id=a.id, target_paper_id=x.id, relation_type="extends", origin="manual"),
    ]
    session.add_all(edges); await session.flush()
    graph = await KnowledgeGraphService(session, {"extends", "supports", "uses"}, {"manual", "ai"}).graph(
        owner.id, paper_id=a.id, depth=2, limit_nodes=200)
    assert {node.paper_id for node in graph.nodes} == {a.id, b.id, c.id}
    assert len(graph.edges) == 3
    manual = await KnowledgeGraphService(session, {"extends", "supports", "uses"}, {"manual"}).graph(
        owner.id, paper_id=a.id, depth=2, limit_nodes=200)
    assert {edge.origin for edge in manual.edges} == {"manual"}
    cites = await KnowledgeGraphService(session, {"cites"}, {"reference"}).graph(
        owner.id, paper_id=c.id, depth=1, limit_nodes=200)
    assert {node.paper_id for node in cites.nodes} == {c.id, d.id}


@pytest.mark.asyncio
async def test_workspace_knowledge_graph_query_count_is_constant_for_scale_fixture(
    session: AsyncSession,
):
    owner = await make_user(session, "kg-scale")
    papers = [await make_paper(session, owner, f"Scale {index:03}") for index in range(80)]
    session.add_all([
        PaperRelation(
            user_id=owner.id,
            source_paper_id=papers[index].id,
            target_paper_id=papers[index + 1].id,
            relation_type="extends",
            origin="manual",
        )
        for index in range(len(papers) - 1)
    ])
    await session.commit()

    query_count = 0

    def count_query(*_args) -> None:
        nonlocal query_count
        query_count += 1

    sync_engine = session.bind.sync_engine
    event.listen(sync_engine, "before_cursor_execute", count_query)
    try:
        graph = await KnowledgeGraphService(
            session, {"extends"}, {"manual"}
        ).graph(owner.id, paper_id=None, depth=1, limit_nodes=20)
    finally:
        event.remove(sync_engine, "before_cursor_execute", count_query)

    assert graph.total_nodes == 80
    assert graph.truncated is True
    assert len(graph.nodes) == 20
    assert query_count <= 10
