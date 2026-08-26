import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPapers,
  getPaper,
  createPaper,
  deletePaper,
  starPaper,
  unstarPaper,
  uploadPaper,
  addTagToPaper,
  addPaperToFolder,
  replacePaperAuthors,
  replacePaperFolders,
  replacePaperTags,
  replacePaperMetadata,
  updatePaper,
  setPaperReadingStatus,
  parseDocument,
} from "./api";
import type { PaperListParams, PaperCreateInput, PaperMetadataDraft, PaperMetadataUpdate, PaperReadingStatus, ReplaceAuthorsRequest, ReplaceFoldersRequest, ReplaceTagsRequest, SaveStage } from "./types";

export function usePapers(params: PaperListParams = {}) {
  return useQuery({
    queryKey: ["papers", params],
    queryFn: () => listPapers(params),
  });
}

export function usePaper(paperId: string | undefined) {
  return useQuery({
    queryKey: ["paper", paperId],
    queryFn: () => getPaper(paperId!),
    enabled: !!paperId,
  });
}

export function useCreatePaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PaperCreateInput) => createPaper(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}

export function useUploadPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (progress: number) => void;
    }) => uploadPaper(file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}

export function useStarPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paperId: string) => starPaper(paperId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}

export function useUnstarPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paperId: string) => unstarPaper(paperId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}

function invalidatePaperData(queryClient: ReturnType<typeof useQueryClient>, paperId: string) {
  queryClient.invalidateQueries({ queryKey: ["papers"] });
  queryClient.invalidateQueries({ queryKey: ["paper-list"] });
  queryClient.invalidateQueries({ queryKey: ["paper", paperId] });
  queryClient.invalidateQueries({ queryKey: ["folders"] });
  queryClient.invalidateQueries({ queryKey: ["tags"] });
}

export function useUpdatePaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, data }: { paperId: string; data: PaperMetadataUpdate }) => updatePaper(paperId, data),
    onSuccess: (_, { paperId }) => invalidatePaperData(queryClient, paperId),
  });
}

export function useReplacePaperAuthors() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, data }: { paperId: string; data: ReplaceAuthorsRequest }) => replacePaperAuthors(paperId, data),
    onSuccess: (_, { paperId }) => invalidatePaperData(queryClient, paperId),
  });
}

export function useReplacePaperTags() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, data }: { paperId: string; data: ReplaceTagsRequest }) => replacePaperTags(paperId, data),
    onSuccess: (_, { paperId }) => invalidatePaperData(queryClient, paperId),
  });
}

export function useReplacePaperFolders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, data }: { paperId: string; data: ReplaceFoldersRequest }) => replacePaperFolders(paperId, data),
    onSuccess: (_, { paperId }) => invalidatePaperData(queryClient, paperId),
  });
}

export function useSavePaperMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ paperId, draft }: { paperId: string; draft: PaperMetadataDraft }) => {
      try {
        return await replacePaperMetadata(paperId, draft);
      } catch (error) {
        throw { stage: "metadata" as SaveStage, error };
      }
    },
    onSettled: async (_, __, { paperId }) => {
      invalidatePaperData(queryClient, paperId);
      await queryClient.refetchQueries({ queryKey: ["paper", paperId] });
    },
  });
}

export function useSetPaperReadingStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, readingStatus }: { paperId: string; readingStatus: PaperReadingStatus }) =>
      setPaperReadingStatus(paperId, readingStatus),
    onSuccess: (_, { paperId }) => invalidatePaperData(queryClient, paperId),
  });
}

export function useParseDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: parseDocument,
    onSuccess: (_, documentId) => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      queryClient.invalidateQueries({ queryKey: ["paper-list"] });
      queryClient.invalidateQueries({ queryKey: ["paper"] });
      queryClient.invalidateQueries({ queryKey: ["document-sections", documentId] });
      queryClient.invalidateQueries({ queryKey: ["document-references", documentId] });
      queryClient.invalidateQueries({ queryKey: ["document-elements", documentId] });
    },
  });
}

export function useDeletePaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paperId: string) => deletePaper(paperId),
    onSuccess: (_, paperId) => {
      queryClient.removeQueries({ queryKey: ["paper", paperId], exact: true });
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}

export function useAddTagToPaper() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, tagId }: { paperId: string; tagId: string }) =>
      addTagToPaper(paperId, tagId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
    },
  });
}

export function useAddPaperToFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paperId, folderId }: { paperId: string; folderId: string }) =>
      addPaperToFolder(paperId, folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      queryClient.invalidateQueries({ queryKey: ["folders"] });
    },
  });
}
