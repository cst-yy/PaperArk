export interface Annotation {
  id: string;
  paper_id: string;
  type: "highlight" | "underline" | "comment";
  content?: string | null;
  page_number: number;
  start_offset?: number | null;
  end_offset?: number | null;
  bbox?: string | null;
  selected_text?: string | null;
  color?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreate {
  paper_id: string;
  document_id?: string;
  type: "highlight" | "underline" | "comment";
  content?: string;
  page_number: number;
  start_offset?: number;
  end_offset?: number;
  bbox?: string;
  selected_text?: string;
  color?: string;
}
