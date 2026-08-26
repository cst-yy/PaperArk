export type PaperListSort = "title" | "title_zh" | "publication_year" | "journal" | "conference" | "citation_count" | "reading_status" | "created_at" | "updated_at";
export type SortOrder = "asc" | "desc";
export type PaperListColumn = "title" | "title_zh" | "abstract" | "authors" | "journal" | "conference" | "publication_year" | "keywords" | "tags" | "folders" | "doi" | "arxiv_id" | "url" | "publisher" | "citation_text" | "citation_count" | "reading_status" | "starred" | "notes" | "created_at" | "updated_at";

export interface NamedItem { id: string; name: string }
export interface PaperListRow {
  id: string; title: string; title_zh: string | null;
  authors: { id: string | null; name: string; affiliation: string | null; author_order: number }[];
  journal: string | null; conference: string | null; publication_year: number | null;
  doi: string | null; arxiv_id: string | null; url: string | null; publisher: string | null;
  abstract: string | null; citation_text: string | null; citation_count: number | null;
  keywords: NamedItem[]; tags: NamedItem[]; folders: NamedItem[];
  status: string; reading_status: string; starred: boolean; note_count: number; has_document: boolean;
  created_at: string; updated_at: string;
  metadata_revision: number;
}
export interface PaperListPage { items: PaperListRow[]; total: number; page: number; page_size: number; total_pages: number }
export interface PaperListQuery {
  q?: string; year_from?: number; year_to?: number; journal?: string; author?: string; tag_id?: string; keyword?: string;
  reading_status?: string; starred?: boolean; sort: PaperListSort; order: SortOrder; page: number; page_size: 25 | 50 | 100 | 200;
}
export interface PaperListPreference { visible_columns: PaperListColumn[]; column_order: PaperListColumn[]; appearance: import("./appearance").PaperListAppearance }
export interface ColumnWidthPreference { preferred_width: number; mode: "auto" | "manual" }
export interface PaperListColumnsSettings { visible: PaperListColumn[]; order: PaperListColumn[]; widths: Partial<Record<PaperListColumn, ColumnWidthPreference>>; layout_version: number }
export interface PaperListLayoutSettings { filters_expanded: boolean; display_sections_expanded: string[]; last_paper_id: string | null; scroll_top: number }
export interface PaperListViewSettings { schema_version: 2; revision: number; columns: PaperListColumnsSettings; appearance: import("./appearance").PaperListAppearance; query: PaperListQuery; layout: PaperListLayoutSettings }
export type PaperListSettingsSection = "columns" | "appearance" | "query" | "layout";
export interface PaperCellUpdate { expected_revision: number; title?: string | null; title_zh?: string | null; abstract?: string | null; journal?: string | null; conference?: string | null; publication_year?: number | null; doi?: string | null; arxiv_id?: string | null; url?: string | null; publisher?: string | null; citation_text?: string | null; citation_count?: number | null; is_starred?: boolean }
