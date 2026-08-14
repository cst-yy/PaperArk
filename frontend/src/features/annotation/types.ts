export type AnnotationType = "highlight" | "underline" | "comment" | "area";
export type AnnotationColor = "yellow" | "green" | "blue" | "red" | "purple";

export interface NormalizedRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TextAnnotationPosition {
  kind: "text";
  rects: NormalizedRect[];
}

export interface AreaAnnotationPosition {
  kind: "area";
  rect: NormalizedRect;
}

export type AnnotationPosition = TextAnnotationPosition | AreaAnnotationPosition;

export interface Annotation {
  id: string;
  paper_id: string;
  document_id: string;
  type: AnnotationType;
  page_number: number;
  selected_text?: string | null;
  prefix_text?: string | null;
  suffix_text?: string | null;
  position_data?: AnnotationPosition | null;
  color?: AnnotationColor | null;
  comment?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAnnotationInput {
  paper_id: string;
  document_id: string;
  type: AnnotationType;
  page_number: number;
  selected_text?: string;
  prefix_text?: string;
  suffix_text?: string;
  position_data?: AnnotationPosition;
  color?: AnnotationColor;
  comment?: string;
}

export interface UpdateAnnotationInput {
  color?: AnnotationColor | null;
  comment?: string | null;
}

export interface SelectionContext {
  pageNumber: number;
  text: string;
  prefixText: string;
  suffixText: string;
  rects: NormalizedRect[];
  toolbarRect: DOMRect;
}
