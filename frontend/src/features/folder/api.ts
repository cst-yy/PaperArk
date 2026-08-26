import { api } from "@/services/api";
import type { Folder, FolderCreateInput, FolderUpdateInput } from "./types";

export async function listFolders(): Promise<Folder[]> {
  const response = await api.get<Folder[]>("/folders/");
  return response.data;
}

export async function createFolder(data: FolderCreateInput): Promise<Folder> {
  const response = await api.post<Folder>("/folders/", data);
  return response.data;
}

export async function deleteFolder(folderId: string): Promise<void> {
  await api.delete(`/folders/${folderId}`);
}
export async function updateFolder(folderId:string,data:FolderUpdateInput):Promise<Folder>{return(await api.patch<Folder>(`/folders/${folderId}`,data)).data;}
