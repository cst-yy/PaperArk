export type PaperProcessingStatus = "imported" | "processing" | "ready" | "failed";
export type PaperReadingStatus = "unread" | "reading" | "finished" | "archived";
export type DocumentParseStatus = "pending" | "processing" | "ready" | "failed";

export interface Author {
  id?: string;
  name: string;
  orcid?: string | null;
  affiliation?: string | null;
  author_order?: number;
}

export interface TagBrief {
  id: string;
  name: string;
  color?: string | null;
}

export interface PaperKeywordBrief {
  id: string;
  display_name: string;
  sources: string[];
}

export interface FolderBrief {
  id: string;
  name: string;
  color?: string | null;
  icon?: string | null;
}

export interface DocumentBrief {
  id: string;
  original_filename: string | null;
  file_size: number | null;
  mime_type: string | null;
  parse_status: DocumentParseStatus;
  parse_error?: string | null;
  parsed_at?: string | null;
  parser_version?: string | null;
}

export interface Paper {
  id: string;
  title: string;
  abstract?: string | null;
  doi?: string | null;
  arxiv_id?: string | null;
  url?: string | null;
  journal?: string | null;
  conference?: string | null;
  publisher?: string | null;
  publication_year?: number | null;
  citation_count?: number | null;
  pdf_path?: string | null;
  cover_path?: string | null;
  status: PaperProcessingStatus;
  reading_status: PaperReadingStatus;
  is_starred: boolean;
  created_at: string;
  updated_at: string;
  authors: Author[];
  tags: TagBrief[];
  folders: FolderBrief[];
  keywords: PaperKeywordBrief[];
  document?: DocumentBrief | null;
  documents: DocumentBrief[];
}

export interface PaperListItem {
  id: string;
  title: string;
  publication_year?: number | null;
  journal?: string | null;
  conference?: string | null;
  status: PaperProcessingStatus;
  reading_status: PaperReadingStatus;
  is_starred: boolean;
  created_at: string;
  first_author?: string | null;
  tags: TagBrief[];
  has_document?: boolean;
}

export interface PaperPage {
  items: PaperListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AuthorInput {
  name: string;
  orcid?: string | null;
  affiliation?: string | null;
}

export interface PaperMetadataUpdate {
  title: string;
  abstract: string | null;
  doi: string | null;
  arxiv_id: string | null;
  url: string | null;
  journal: string | null;
  conference: string | null;
  publisher: string | null;
  publication_year: number | null;
  citation_count: number | null;
}

export interface ReplaceAuthorsRequest {
  authors: AuthorInput[];
}

export interface ReplaceTagsRequest {
  tag_ids: string[];
}

export interface ReplaceFoldersRequest {
  folder_ids: string[];
}

export interface PaperMetadataDraft extends PaperMetadataUpdate {
  authors: AuthorInput[];
  tag_ids: string[];
  folder_ids: string[];
  keywords: { name: string }[];
}

export type SaveStage = "metadata";

export interface PaperListParams {
  q?: string;
  folder_id?: string;
  tag_id?: string;
  year?: number;
  starred?: boolean;
  status?: PaperProcessingStatus;
  reading_status?: PaperReadingStatus;
  page?: number;
  page_size?: number;
}

export interface PaperCreateInput {
  title: string;
  abstract?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  journal?: string;
  conference?: string;
  publisher?: string;
  publication_year?: number;
  citation_count?: number;
  authors?: Author[];
  tag_ids?: string[];
  folder_ids?: string[];
}
