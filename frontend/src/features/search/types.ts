export type SearchSource = "title" | "abstract" | "author" | "tag" | "keyword" | "doi" | "arxiv" | "journal" | "conference" | "publisher" | "section" | "chunk" | "reference" | "figure" | "table";

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
  paper: { id: string; title: string; publication_year: number | null; authors: string[] };
  score: number;
  match_count: number;
  matches: SearchMatch[];
}

export interface SearchPageResponse {
  items: SearchPaperResult[];
  total: number;
  page: number;
  page_size: number;
}
