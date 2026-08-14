export type SearchSource = "title" | "abstract" | "author" | "tag" | "keyword" | "doi" | "arxiv" | "journal" | "conference" | "publisher" | "section" | "chunk" | "reference" | "figure" | "table" | "note_title" | "note_content" | "research_background" | "research_problem" | "research_method" | "research_contribution" | "research_experiment" | "research_conclusion" | "research_thought";

export interface SearchMatch {
  source: SearchSource;
  text: string;
  snippet: string | null;
  document_id: string | null;
  page_start: number | null;
  page_end: number | null;
  section_id: string | null;
}

export interface SearchPaperResult {
  entity_type: "paper";
  paper: { id: string; title: string; publication_year: number | null; authors: string[] };
  score: number;
  match_count: number;
  matches: SearchMatch[];
}

export interface SearchNoteResult {
  entity_type: "note";
  note: { id: string; title: string; note_type: "general" | "paper" | "research"; paper_id: string | null; paper_title: string | null };
  score: number;
  match_count: number;
  matches: SearchMatch[];
}

export type SearchResult = SearchPaperResult | SearchNoteResult;

export interface SearchPageResponse {
  items: SearchResult[];
  total: number;
  page: number;
  page_size: number;
}
