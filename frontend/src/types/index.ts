export interface Folder {
  id: string;
  name: string;
  parent_id?: string | null;
  color?: string | null;
  icon?: string | null;
  sort_order: number;
  paper_count?: number;
  children?: Folder[];
}

export interface Tag {
  id: string;
  name: string;
  color?: string | null;
  paper_count?: number;
}

export interface Section {
  id: string;
  document_id: string;
  parent_id?: string | null;
  title: string;
  section_type?: string | null;
  level: number;
  page_start?: number | null;
  page_end?: number | null;
  order_index: number;
  children: Section[];
}

export interface DocumentBrief {
  id: string;
  original_filename?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  parse_status: string;
}

/** API representation returned by GET /api/documents/{id}. */
export interface DocumentDetail extends DocumentBrief {
  paper_id: string;
  page_count?: number | null;
  parse_error?: string | null;
  parsed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type PaperStatus = "imported" | "processing" | "ready" | "failed";

export type RelationType =
  | "cites"
  | "cited_by"
  | "related"
  | "same_topic"
  | "extends"
  | "improves"
  | "baseline";
