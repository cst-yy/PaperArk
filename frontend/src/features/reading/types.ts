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
}

export interface RecentReadingItem {
  paper: {
    id: string;
    title: string;
    publication_year: number | null;
    authors: string[];
    is_starred: boolean;
  };
  document: {
    id: string;
  };
  current_page: number;
  total_pages: number;
  progress_ratio: number;
  last_read_at: string;
}
