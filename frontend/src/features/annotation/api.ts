import { api } from "@/services/api";

import type { Annotation, CreateAnnotationInput, UpdateAnnotationInput } from "./types";

export async function listAnnotations(
  paperId: string,
  documentId?: string,
  pageNumber?: number,
): Promise<Annotation[]> {
  const response = await api.get<Annotation[]>("/annotations/", {
    params: { paper_id: paperId, document_id: documentId, page_number: pageNumber },
  });
  return response.data;
}

export async function createAnnotation(input: CreateAnnotationInput): Promise<Annotation> {
  const response = await api.post<Annotation>("/annotations/", input);
  return response.data;
}

export async function updateAnnotation(
  annotationId: string,
  input: UpdateAnnotationInput,
): Promise<Annotation> {
  const response = await api.patch<Annotation>(`/annotations/${annotationId}`, input);
  return response.data;
}

export async function deleteAnnotation(annotationId: string): Promise<void> {
  await api.delete(`/annotations/${annotationId}`);
}
