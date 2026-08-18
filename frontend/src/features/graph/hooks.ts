import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { decideSuggestion, generateSuggestions, getCitationEdge, getCitationGraph, getGraphLayout, getKnowledgeGraph, getMindMap, getRelation, listSuggestions, saveGraphLayout } from "./api";
import type { GraphLayout, Point } from "./types";

export function useCitationGraph(paperId: string | undefined, depth: 1 | 2) {
  return useQuery({ queryKey: ["citation-graph", paperId ?? "workspace", depth], queryFn: () => getCitationGraph({ paperId, depth }) });
}

export function useCitationEdge(relationId?: string) {
  return useQuery({ queryKey: ["citation-edge", relationId ?? "none"], queryFn: () => getCitationEdge(relationId!), enabled: Boolean(relationId) });
}

export function useKnowledgeGraph(paperId: string | undefined, depth: 1 | 2, relationTypes: string[], origins: string[]) {
  return useQuery({ queryKey: ["knowledge-graph", paperId ?? "workspace", depth, relationTypes, origins], queryFn: () => getKnowledgeGraph({ paperId, depth, relationTypes, origins }) });
}
export function useKnowledgeRelation(id?: string) { return useQuery({ queryKey: ["knowledge-relation", id], queryFn: () => getRelation(id!), enabled: Boolean(id) }); }
export function useGraphLayout(graphType: GraphLayout["graph_type"], scopeKey: string) { return useQuery({ queryKey: ["graph-layout", graphType, scopeKey], queryFn: () => getGraphLayout(graphType, scopeKey) }); }
export function useSaveGraphLayout() { const client = useQueryClient(); return useMutation({ mutationFn: ({ graphType, scopeKey, positions }: { graphType: GraphLayout["graph_type"]; scopeKey: string; positions: Record<string, Point> }) => saveGraphLayout(graphType, scopeKey, positions), onSuccess: (data) => client.setQueryData(["graph-layout", data.graph_type, data.scope_key], data) }); }
export function useSuggestions(paperId?: string) { return useQuery({ queryKey: ["relation-suggestions", paperId], queryFn: () => listSuggestions(paperId!), enabled: Boolean(paperId) }); }
export function useGenerateSuggestions(paperId?: string) { const client = useQueryClient(); return useMutation({ mutationFn: () => generateSuggestions(paperId!), onSuccess: () => client.invalidateQueries({ queryKey: ["relation-suggestions", paperId] }) }); }
export function useDecideSuggestion(paperId?: string) { const client = useQueryClient(); return useMutation({ mutationFn: ({ id, decision }: { id: string; decision: "accept" | "reject" }) => decideSuggestion(id, decision), onSuccess: () => { client.invalidateQueries({ queryKey: ["relation-suggestions", paperId] }); client.invalidateQueries({ queryKey: ["knowledge-graph"] }); } }); }
export function useMindMap(paperId?: string) { return useQuery({ queryKey: ["mind-map", paperId], queryFn: () => getMindMap(paperId!), enabled: Boolean(paperId) }); }
