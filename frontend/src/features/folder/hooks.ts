import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listFolders, createFolder, deleteFolder } from "./api";
import type { FolderCreateInput } from "./types";

export function useFolders() {
  return useQuery({
    queryKey: ["folders"],
    queryFn: () => listFolders(),
  });
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FolderCreateInput) => createFolder(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
    },
  });
}

export function useDeleteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (folderId: string) => deleteFolder(folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
    },
  });
}
