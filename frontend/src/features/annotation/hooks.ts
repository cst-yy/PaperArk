import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createAnnotation, deleteAnnotation, listAnnotations, updateAnnotation } from "./api";
import type { CreateAnnotationInput, UpdateAnnotationInput } from "./types";

export function annotationQueryKey(
  paperId: string,
  documentId?: string,
  pageNumber?: number | "all",
) {
  return ["annotations", paperId, documentId ?? "all-documents", pageNumber ?? "all"] as const;
}

export function useAnnotations(
  paperId: string | undefined,
  documentId?: string,
  pageNumber?: number,
) {
  return useQuery({
    queryKey: paperId ? annotationQueryKey(paperId, documentId, pageNumber) : ["annotations", "disabled"],
    queryFn: () => listAnnotations(paperId!, documentId, pageNumber),
    enabled: Boolean(paperId && documentId),
  });
}

export function useCreateAnnotation(paperId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAnnotationInput) => createAnnotation(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["annotations", paperId] });
    },
  });
}

export function useUpdateAnnotation(paperId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ annotationId, input }: { annotationId: string; input: UpdateAnnotationInput }) =>
      updateAnnotation(annotationId, input),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["annotations", paperId] }),
  });
}

export function useDeleteAnnotation(paperId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (annotationId: string) => deleteAnnotation(annotationId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["annotations", paperId] }),
  });
}
