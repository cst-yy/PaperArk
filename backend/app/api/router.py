from fastapi import APIRouter

from app.api.endpoints import (
    ai,
    ai_infrastructure,
    ai_chat,
    annotations,
    documents,
    dashboard,
    embeddings,
    folders,
    graph,
    keywords,
    knowledge_relations,
    notes,
    paper_list,
    papers,
    rag,
    reading,
    search,
    tags,
    translations,
    workspace,
    todos,
    memos,
    research_identity,
    my_papers,
)

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(todos.router, prefix="/todos", tags=["todos"])
api_router.include_router(memos.router, prefix="/memos", tags=["memos"])
api_router.include_router(research_identity.router, prefix="/research-identity", tags=["research-identity"])
api_router.include_router(my_papers.router, prefix="/my-papers", tags=["my-papers"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(paper_list.router, prefix="/paper-list", tags=["paper-list"])
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
api_router.include_router(ai_infrastructure.router, prefix="/ai", tags=["ai-infrastructure"])
api_router.include_router(ai_chat.router, tags=["ai-chat"])
api_router.include_router(translations.router, tags=["translations"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(knowledge_relations.router, prefix="/paper-relations", tags=["knowledge-relations"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
