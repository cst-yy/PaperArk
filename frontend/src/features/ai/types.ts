export interface AISummary {
  paper_id: string;
  tldr: string;
  key_points: string[];
  methods?: string | null;
  contribution?: string | null;
}

export interface AIQA {
  paper_id: string;
  question: string;
  answer: string;
  sources: Array<{
    page?: number;
    section?: string;
    content?: string;
  }>;
}
