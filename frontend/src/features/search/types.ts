export interface SearchResult {
  paper_id: string;
  title: string;
  snippet: string;
  page_number?: number | null;
  section_title?: string | null;
  score: number;
  source?: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}
