import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listTags, createTag, deleteTag, updateTag } from "./api";
import type { TagCreateInput, TagUpdateInput } from "./types";

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: () => listTags(),
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TagCreateInput) => createTag(data),
    onSuccess: () => invalidateTagRelatedData(queryClient),
  });
}

function invalidateTagRelatedData(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["tags"] });
  queryClient.invalidateQueries({ queryKey: ["papers"] });
  queryClient.invalidateQueries({ queryKey: ["paper"] });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, data }: { tagId: string; data: TagUpdateInput }) => updateTag(tagId, data),
    onSuccess: () => invalidateTagRelatedData(queryClient),
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) => deleteTag(tagId),
    onSuccess: () => invalidateTagRelatedData(queryClient),
  });
}
