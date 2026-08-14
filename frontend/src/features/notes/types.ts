export type NoteType = "general" | "paper" | "research";

export interface Note {
  id: string;
  user_id: string;
  paper_id: string | null;
  title: string;
  content_markdown: string;
  note_type: NoteType;
  created_at: string;
  updated_at: string;
  evidence: NoteEvidence[];
}

export interface EvidenceAnnotation {
  id: string;
  type: "highlight" | "underline" | "comment" | "area";
  selected_text?: string | null;
  comment?: string | null;
  page_number: number;
  document_id: string;
  paper_id: string;
}

export interface NoteEvidence {
  id: string;
  annotation_id: string;
  order_index: number;
  quote_snapshot?: string | null;
  created_at: string;
  annotation: EvidenceAnnotation;
}

export interface NoteCreate {
  paper_id?: string | null;
  title?: string;
  content_markdown?: string;
  note_type?: NoteType;
  annotation_ids?: string[];
}

export interface NoteUpdate {
  paper_id?: string | null;
  title?: string;
  content_markdown?: string;
  note_type?: NoteType;
}

export interface NoteAggregate {
  paper_id: string | null;
  title: string;
  content_markdown: string;
  note_type: NoteType;
}
