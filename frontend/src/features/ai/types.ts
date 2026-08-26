export type RetrievalMode = "lexical" | "semantic" | "hybrid";
export type TargetLanguage = "zh-CN" | "en";

export interface AICitation {
  label: string;
  source_key: string;
  source_type: "paper_chunk" | "note";
  paper_id?: string | null;
  paper_title?: string | null;
  document_id?: string | null;
  note_id?: string | null;
  title: string;
  section_title?: string | null;
  page_start?: number | null;
  page_end?: number | null;
}

export interface PaperQAResponse {
  paper_id: string;
  query: string;
  answer: string;
  citations: AICitation[];
  grounded: boolean;
  insufficient_evidence: boolean;
  requested_mode: RetrievalMode;
  effective_mode: RetrievalMode;
}
export interface AIChatSession { id:string; paper_id:string; title:string; scope_type:"selection"|"page"|"section"|"paper"; scope_snapshot:Record<string,unknown>|null; model_id:string|null; created_at:string; updated_at:string; last_message_at:string|null; }
export interface AIMessageCitation { id:string; paper_id:string; section_id:string|null; chunk_id:string|null; page_block_id:string|null; page_number:number|null; quote_text:string; bounding_box:Record<string,number>|null; citation_order:number; }
export interface AIChatMessage { id:string; session_id:string; role:"user"|"assistant"; content:string; status:string; request_record_id:string|null; input_scope_snapshot:Record<string,unknown>|null; created_at:string; citations:AIMessageCitation[]; }
export interface AIChatTurn { user_message:AIChatMessage; assistant_message:AIChatMessage; }

export interface TranslationResult {
  translated_text: string;
  source_language?: string | null;
  target_language: TargetLanguage;
}

export interface GroundedStructuredField {
  content: string;
  evidence_refs: string[];
  insufficient_evidence: boolean;
  grounded: boolean;
}

export interface DeepReadingContribution {
  client_id: string;
  problem: string;
  prior_limitation: string;
  innovation: string;
  solution: string;
  evidence_refs: string[];
  insufficient_evidence: boolean;
  grounded: boolean;
}

export interface DeepReadingExperiment {
  client_id: string;
  task: string;
  datasets: string[];
  baselines: string[];
  metrics: string[];
  result: string;
  conclusion: string;
  supports_contribution_client_ids: string[];
  evidence_refs: string[];
  insufficient_evidence: boolean;
  grounded: boolean;
}

export interface DeepReadingDraft {
  paper_id: string;
  requested_mode: RetrievalMode;
  effective_mode: RetrievalMode;
  background: GroundedStructuredField;
  prior_work_limitations: GroundedStructuredField;
  research_problem: GroundedStructuredField;
  method_summary: GroundedStructuredField;
  results_summary: GroundedStructuredField;
  conclusion: GroundedStructuredField;
  limitations: GroundedStructuredField;
  future_work: GroundedStructuredField;
  contributions: DeepReadingContribution[];
  experiments: DeepReadingExperiment[];
  sources: AICitation[];
  source_count: number;
  analysis_id?: string | null;
  provider_name?: string | null;
  model?: string | null;
  prompt_version?: string | null;
  source_snapshot_hash?: string | null;
  input_hash?: string | null;
  created_at?: string | null;
}

export interface AIAnalysisBrief {
  analysis_id: string;
  analysis_type: "deep_reading";
  status: "ready";
  provider_name: string;
  model: string;
  prompt_version: string;
  retrieval_mode: RetrievalMode;
  source_count: number;
  application_count: number;
  source_snapshot_hash: string;
  created_at: string;
}

export interface AIAnalysisSourceSnapshot extends AICitation {
  content_snapshot: string;
  content_hash: string;
  chunk_id?: string | null;
  retrieval_score?: number | null;
}

export interface AIAnalysisDetail {
  draft: DeepReadingDraft;
  source_snapshots: AIAnalysisSourceSnapshot[];
}

export type AIApplicableScalar = Exclude<keyof Pick<DeepReadingDraft,
  "background" | "prior_work_limitations" | "research_problem" | "method_summary" |
  "results_summary" | "conclusion" | "limitations" | "future_work">, never>;

export interface AIAnalysisApplyRequest {
  note_id: string;
  apply: {
    scalar_fields: AIApplicableScalar[];
    contribution_client_ids: string[];
    experiment_client_ids: string[];
  };
  scalar_conflict_policy: "fill_empty" | "replace";
  collections_mode: "append" | "replace";
  expected_revision: number;
}
