export interface Note {
  id: string;
  paper_id: string;
  title?: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface NoteCreate {
  paper_id: string;
  title?: string;
  content?: string;
}

export interface NoteUpdate {
  title?: string;
  content?: string;
}
