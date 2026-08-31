export interface ReadingProgress {
  paper_id: string;
  document_id: string;
  current_page: number;
  total_pages: number;
  progress_ratio: number;
  last_read_at: string;
  reading_time_seconds: number;
}

export interface ReadingProgressUpsert {
  document_id: string;
  current_page: number;
  total_pages: number;
  reading_time_seconds_delta?: number;
}

export interface RecentReadingItem {
  paper: {
    id: string;
    title: string;
    publication_year: number | null;
    authors: string[];
    is_starred: boolean;
    my_author_roles?: { author_order:number; is_first_author:boolean; is_co_first:boolean; is_corresponding:boolean } | null;
  };
  document: {
    id: string;
  };
  current_page: number;
  total_pages: number;
  progress_ratio: number;
  last_read_at: string;
}
