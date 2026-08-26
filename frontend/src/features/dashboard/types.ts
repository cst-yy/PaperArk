export interface DashboardOverview {
  total_papers: number;
  reading_papers: number;
  finished_papers: number;
  research_notes: number;
}

export interface DashboardRecentReading {
  paper_id: string;
  title: string;
  publication_year: number | null;
  author: string | null;
  document_id: string;
  current_page: number;
  total_pages: number;
  progress_ratio: number;
  last_read_at: string;
}

export interface DashboardRecentPaper {
  id: string;
  title: string;
  publication_year: number | null;
  author: string | null;
  reading_status: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardRecentNote {
  id: string;
  title: string;
  note_type: string;
  paper_id: string | null;
  paper_title: string | null;
  updated_at: string;
}

export interface DashboardTopicStat {
  id: string;
  name: string;
  paper_count: number;
}

export interface DashboardData {
  overview: DashboardOverview;
  recent_reading: DashboardRecentReading[];
  recent_papers: DashboardRecentPaper[];
  recent_notes: DashboardRecentNote[];
  tags: DashboardTopicStat[];
  keywords: DashboardTopicStat[];
  backup: { last_backup_at: string | null };
}

export interface ReadingTrend {
  days: 7 | 30 | 90;
  daily: { date: string; papers_read: number; reading_time_seconds: number }[];
  summary: { papers_read: number; active_days: number; reading_time_seconds: number };
}
