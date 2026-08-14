export interface Keyword {
  id: string;
  display_name: string;
  created_at: string;
}

export interface KeywordInput {
  name: string;
}

export interface PaperKeywordBrief {
  id: string;
  display_name: string;
  sources: string[];
}
