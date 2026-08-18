import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.core.exceptions import PaperNotFoundError
from app.schemas.citation_graph import CitationEdgeDetail, CitationGraphResponse
from app.services.citation_graph_service import CitationGraphService
from app.schemas.knowledge_graph import KnowledgeGraphResponse
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.schemas.graph_layout import GraphLayoutResponse, GraphLayoutSave
from app.services.graph_layout_service import GraphLayoutService

router = APIRouter()


@router.get("/layout", response_model=GraphLayoutResponse | None)
async def get_graph_layout(
    graph_type: str = Query(..., pattern="^(citation|knowledge|mind_map)$"),
    scope_key: str = Query(..., min_length=1, max_length=500),
    db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await GraphLayoutService(db).get(user_id, graph_type, scope_key)


@router.put("/layout", response_model=GraphLayoutResponse)
async def save_graph_layout(
    data: GraphLayoutSave, db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await GraphLayoutService(db).save(user_id, data)

KNOWLEDGE_TYPES = {"extends", "improves", "contrasts", "supports", "uses", "similar"}
ALL_TYPES = KNOWLEDGE_TYPES | {"cites"}
ALL_ORIGINS = {"reference", "manual", "ai"}


def _csv(value: str | None, default: set[str], allowed: set[str], label: str) -> set[str]:
    result = {item.strip() for item in value.split(",") if item.strip()} if value else default
    unknown = result - allowed
    if unknown: raise HTTPException(status_code=422, detail=f"Unknown {label}: {', '.join(sorted(unknown))}")
    return result


@router.get("/knowledge", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    paper_id: uuid.UUID | None = Query(None), depth: int = Query(1, ge=1, le=2),
    limit_nodes: int = Query(200, ge=10, le=500),
    relation_types: str | None = Query(None), origins: str | None = Query(None),
    db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id),
):
    types = _csv(relation_types, KNOWLEDGE_TYPES, ALL_TYPES, "relation type")
    selected_origins = _csv(origins, {"manual", "ai"}, ALL_ORIGINS, "origin")
    try:
        return await KnowledgeGraphService(db, types, selected_origins).graph(
            user_id, paper_id=paper_id, depth=depth, limit_nodes=limit_nodes)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error


@router.get("/citations", response_model=CitationGraphResponse)
async def get_citation_graph(
    paper_id: uuid.UUID | None = Query(None), depth: int = Query(1, ge=1, le=2),
    limit_nodes: int = Query(200, ge=10, le=500),
    db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        return await CitationGraphService(db).graph(
            user_id, paper_id=paper_id, depth=depth, limit_nodes=limit_nodes
        )
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=error.message) from error


@router.get("/citations/edges/{relation_id}", response_model=CitationEdgeDetail)
async def get_citation_edge(
    relation_id: uuid.UUID, db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    detail = await CitationGraphService(db).edge_detail(user_id, relation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Citation edge not found")
    return detail
