import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError
from app.models import Author, Document, Paper, PaperAuthor, PaperRelation, Reference, User
from app.services.citation_graph_service import CitationGraphService


async def make_user(session: AsyncSession, name: str) -> User:
    value = User(id=uuid.uuid4(), username=name, email=f"{name}@test.local", password_hash="")
    session.add(value); await session.flush(); return value


async def make_paper(session: AsyncSession, owner: User, title: str) -> Paper:
    value = Paper(user_id=owner.id, title=title, status="ready")
    session.add(value); await session.flush()
    author = Author(name=f"Author {title}")
    session.add(author); await session.flush()
    session.add(PaperAuthor(paper_id=value.id, author_id=author.id, author_order=0))
    await session.flush(); return value


async def cite(session: AsyncSession, owner: User, source: Paper, target: Paper, order: int) -> PaperRelation:
    document = Document(paper_id=source.id, file_path=f"pdfs/{source.id}-{order}.pdf", parse_status="ready")
    session.add(document); await session.flush()
    reference = Reference(document_id=document.id, order_index=0, raw_text=f"{source.title} cites {target.title}",
        title=target.title, page_start=1, page_end=1, matched_paper_id=target.id,
        match_method="title_exact", match_confidence=0.95)
    session.add(reference); await session.flush()
    relation = PaperRelation(user_id=owner.id, source_paper_id=source.id, target_paper_id=target.id,
        relation_type="cites", origin="reference", source_reference_id=reference.id, confidence=0.95)
    session.add(relation); await session.flush(); return relation


@pytest.mark.asyncio
async def test_root_depth_bidirectional_bfs_and_induced_subgraph(session: AsyncSession) -> None:
    owner = await make_user(session, "graph-owner")
    a, b, c, d, x, isolated = [await make_paper(session, owner, value) for value in "ABCDXI"]
    ab = await cite(session, owner, a, b, 0)
    await cite(session, owner, a, c, 1)
    await cite(session, owner, b, c, 2)
    await cite(session, owner, c, d, 3)
    await cite(session, owner, x, a, 4)
    await session.commit()
    service = CitationGraphService(session)

    depth1 = await service.graph(owner.id, paper_id=a.id, depth=1, limit_nodes=200)
    assert {node.paper_id for node in depth1.nodes} == {a.id, b.id, c.id, x.id}
    assert {(edge.source_paper_id, edge.target_paper_id) for edge in depth1.edges} == {
        (a.id, b.id), (a.id, c.id), (b.id, c.id), (x.id, a.id),
    }
    node_a = next(node for node in depth1.nodes if node.paper_id == a.id)
    assert node_a.incoming_count == 1 and node_a.outgoing_count == 2
    assert node_a.authors == ["Author A"]

    depth2 = await service.graph(owner.id, paper_id=a.id, depth=2, limit_nodes=200)
    assert {node.paper_id for node in depth2.nodes} == {a.id, b.id, c.id, d.id, x.id}
    assert len(depth2.edges) == 5
    assert isolated.id not in {node.paper_id for node in depth2.nodes}
    detail = await service.edge_detail(owner.id, ab.id)
    assert detail and detail.match_method == "title_exact" and detail.raw_citation == "A cites B"


@pytest.mark.asyncio
async def test_cycle_safe_workspace_scope_and_isolated_root(session: AsyncSession) -> None:
    owner = await make_user(session, "cycle-owner")
    foreign = await make_user(session, "cycle-foreign")
    a, b, c, isolated = [await make_paper(session, owner, value) for value in ("A", "B", "C", "Isolated")]
    foreign_paper = await make_paper(session, foreign, "Foreign")
    await cite(session, owner, a, b, 0)
    await cite(session, owner, b, c, 1)
    await cite(session, owner, c, a, 2)
    # Deliberately malformed cross-owner row proves defensive endpoint scoping.
    session.add(PaperRelation(user_id=owner.id, source_paper_id=a.id, target_paper_id=foreign_paper.id,
        relation_type="cites", origin="reference"))
    await session.commit()
    service = CitationGraphService(session)

    graph = await service.graph(owner.id, paper_id=a.id, depth=2, limit_nodes=200)
    assert {node.paper_id for node in graph.nodes} == {a.id, b.id, c.id}
    assert len(graph.edges) == 3
    workspace = await service.graph(owner.id, paper_id=None, depth=1, limit_nodes=200)
    assert {node.paper_id for node in workspace.nodes} == {a.id, b.id, c.id}
    assert isolated.id not in {node.paper_id for node in workspace.nodes}
    lonely = await service.graph(owner.id, paper_id=isolated.id, depth=1, limit_nodes=200)
    assert [node.paper_id for node in lonely.nodes] == [isolated.id] and lonely.edges == []
    with pytest.raises(PaperNotFoundError):
        await service.graph(owner.id, paper_id=foreign_paper.id, depth=1, limit_nodes=200)


@pytest.mark.asyncio
async def test_deterministic_truncation_keeps_root_and_filters_induced_edges(session: AsyncSession) -> None:
    owner = await make_user(session, "limit-owner")
    root = await make_paper(session, owner, "Root")
    neighbors = [await make_paper(session, owner, f"N{index:02}") for index in range(12)]
    for index, target in enumerate(neighbors):
        await cite(session, owner, root, target, index)
    await session.commit()
    service = CitationGraphService(session)
    first = await service.graph(owner.id, paper_id=root.id, depth=1, limit_nodes=10)
    second = await service.graph(owner.id, paper_id=root.id, depth=1, limit_nodes=10)
    assert first.truncated is True and first.total_nodes == 13 and len(first.nodes) == 10
    assert first.nodes[0].paper_id == root.id
    assert [node.paper_id for node in first.nodes] == [node.paper_id for node in second.nodes]
    selected = {node.paper_id for node in first.nodes}
    assert all(edge.source_paper_id in selected and edge.target_paper_id in selected for edge in first.edges)
