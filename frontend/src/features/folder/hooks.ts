import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listFolders, createFolder, deleteFolder, updateFolder } from "./api";
import type { FolderCreateInput, FolderUpdateInput } from "./types";

export function useFolders() {
  return useQuery({
    queryKey: ["folders"],
    queryFn: () => listFolders(),
  });
}
export function useUpdateFolder(){const queryClient=useQueryClient();return useMutation({mutationFn:({folderId,data}:{folderId:string;data:FolderUpdateInput})=>updateFolder(folderId,data),onSuccess:()=>queryClient.invalidateQueries({queryKey:["folders"]})});}

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
