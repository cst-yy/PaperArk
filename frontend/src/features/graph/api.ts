import { api } from "@/services/api";
import type { CitationEdgeDetail, CitationGraph, GraphLayout, KnowledgeGraph, KnowledgeRelation, KnowledgeRelationType, MindMap, RelationSuggestion, Point } from "./types";

export async function getCitationGraph(input: { paperId?: string; depth: 1 | 2; limitNodes?: number }): Promise<CitationGraph> {
  return (await api.get<CitationGraph>("/graph/citations", { params: {
    paper_id: input.paperId, depth: input.depth, limit_nodes: input.limitNodes ?? 200,
  } })).data;
}

export async function getCitationEdge(relationId: string): Promise<CitationEdgeDetail> {
  return (await api.get<CitationEdgeDetail>(`/graph/citations/edges/${relationId}`)).data;
}

export async function getKnowledgeGraph(input: { paperId?: string; depth: 1 | 2; relationTypes: string[]; origins: string[] }): Promise<KnowledgeGraph> {
  return (await api.get<KnowledgeGraph>("/graph/knowledge", { params: { paper_id: input.paperId,
    depth: input.depth, relation_types: input.relationTypes.join(","), origins: input.origins.join(","), limit_nodes: 200 } })).data;
}
export async function getRelation(id: string) { return (await api.get<KnowledgeRelation>(`/paper-relations/${id}`)).data; }
export async function createRelation(sourceId: string, data: { target_paper_id: string; relation_type: KnowledgeRelationType; note?: string | null }) { return (await api.post<KnowledgeRelation>(`/papers/${sourceId}/relations`, data)).data; }
export async function updateRelation(sourceId: string, id: string, data: { target_paper_id: string; relation_type: KnowledgeRelationType; note?: string | null }) { return (await api.put<KnowledgeRelation>(`/papers/${sourceId}/relations/${id}`, data)).data; }
export async function deleteRelation(sourceId: string, id: string) { await api.delete(`/papers/${sourceId}/relations/${id}`); }
export async function replaceRelationEvidence(id: string, evidence: Array<{ annotation_id?: string; source_reference_id?: string }>) { return (await api.put<KnowledgeRelation>(`/paper-relations/${id}/evidence`, { evidence })).data; }
export async function listSuggestions(paperId: string) { return (await api.get<RelationSuggestion[]>(`/papers/${paperId}/relation-suggestions`)).data; }
export async function generateSuggestions(paperId: string) { return (await api.post<RelationSuggestion[]>(`/papers/${paperId}/relation-suggestions/generate`, { max_candidates: 5 })).data; }
export async function decideSuggestion(id: string, decision: "accept" | "reject") { return (await api.post<RelationSuggestion>(`/paper-relations/suggestions/${id}/${decision}`)).data; }
export async function getGraphLayout(graphType: GraphLayout["graph_type"], scopeKey: string) { return (await api.get<GraphLayout | null>("/graph/layout", { params: { graph_type: graphType, scope_key: scopeKey } })).data; }
export async function saveGraphLayout(graphType: GraphLayout["graph_type"], scopeKey: string, positions: Record<string, Point>) { return (await api.put<GraphLayout>("/graph/layout", { graph_type: graphType, scope_key: scopeKey, positions })).data; }
export async function getMindMap(paperId: string) { return (await api.get<MindMap>(`/papers/${paperId}/mind-map`)).data; }
