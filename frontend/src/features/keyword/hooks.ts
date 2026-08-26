import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteKeyword, listKeywords } from "./api";

export const keywordKeys = {
  all: ["keywords"] as const,
};

export function useKeywords() {
  return useQuery({ queryKey: keywordKeys.all, queryFn: listKeywords });
}

export function useDeleteKeyword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteKeyword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keywordKeys.all });
      queryClient.invalidateQueries({ queryKey: ["papers"] });
      queryClient.invalidateQueries({ queryKey: ["paper"] });
    },
  });
}
