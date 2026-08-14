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
}
