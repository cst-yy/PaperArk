from fastapi import APIRouter

from app.api.endpoints import (
    ai,
    annotations,
    documents,
    embeddings,
    folders,
    keywords,
    notes,
    papers,
    rag,
    reading,
    search,
    tags,
    workspace,
)

api_router = APIRouter()

api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(reading.router, prefix="/reading", tags=["reading"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(
    annotations.router, prefix="/annotations", tags=["annotations"]
)
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
