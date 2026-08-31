export interface CitationGraphNode {
  paper_id: string;
  title: string;
  publication_year?: number | null;
  authors: string[];
  is_starred: boolean;
  reading_status: string;
  incoming_count: number;
  outgoing_count: number;
}

export interface CitationGraphEdge {
  relation_id: string;
  source_paper_id: string;
  target_paper_id: string;
  relation_type: "cites";
  origin: "reference";
  confidence?: number | null;
  source_reference_id?: string | null;
}

export interface CitationGraph {
  root_paper_id?: string | null;
  depth: 1 | 2;
  nodes: CitationGraphNode[];
  edges: CitationGraphEdge[];
  truncated: boolean;
  total_nodes: number;
}

export interface CitationEdgeDetail {
  edge: CitationGraphEdge;
  raw_citation?: string | null;
  reference_order?: number | null;
  match_method?: string | null;
}

export type KnowledgeRelationType = "extends" | "improves" | "contrasts" | "supports" | "uses" | "similar";
export type GraphRelationType = "cites" | KnowledgeRelationType;
export type RelationOrigin = "reference" | "manual" | "ai";
export type Point = { x: number; y: number; width?: number; height?: number; background?: string; text_color?: string; font_size?: number };

export interface KnowledgeGraphEdge {
  relation_id: string;
  source_paper_id: string;
  target_paper_id: string;
  relation_type: GraphRelationType;
  origin: RelationOrigin;
  confidence?: number | null;
  note?: string | null;
  evidence_count: number;
}

export interface KnowledgeGraph extends Omit<CitationGraph, "edges"> { edges: KnowledgeGraphEdge[] }

export interface RelationEvidence {
  id: string;
  annotation_id?: string | null;
  source_reference_id?: string | null;
  quote_snapshot: string;
  order_index: number;
  paper_id?: string | null; document_id?: string | null; page_number?: number | null;
}

export interface KnowledgeRelation {
  id: string; source_paper_id: string; target_paper_id: string;
  relation_type: GraphRelationType; origin: RelationOrigin; note?: string | null;
  confidence?: number | null; evidence: RelationEvidence[]; ai_evidence: Record<string, unknown>[];
  ai_provider_name?: string | null; ai_model?: string | null; created_at: string;
}

export interface RelationSuggestion {
  id: string; source_paper_id: string; target_paper_id: string; relation_type: KnowledgeRelationType;
  status: "pending" | "accepted" | "rejected"; confidence?: number | null; reason: string;
  evidence: Array<{ paper_id?: string; document_id?: string; section_id?: string | null; chunk_id?: string; page_start?: number; page_end?: number; content?: string }>;
  provider_name: string; model: string; accepted_relation_id?: string | null; created_at: string;
}

export interface GraphLayout { id: string; graph_type: "citation" | "knowledge" | "mind_map"; scope_key: string; positions: Record<string, Point>; updated_at: string }

export interface MindMapNode { id: string; node_type: "paper" | "profile_field" | "contribution" | "experiment" | "manual"; title: string; summary: string; paper_id: string; note_id?: string | null; entity_id?: string | null; evidence_ids: string[] }
export interface MindMapEdge { id?: string | null; source: string; target: string; relation: string; manual?: boolean }
export interface MindMap { paper_id: string; note_id?: string | null; profile_revision?: number | null; nodes: MindMapNode[]; edges: MindMapEdge[]; has_profile: boolean }
