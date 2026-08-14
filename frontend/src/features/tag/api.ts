import { api } from "@/services/api";
import type { Tag, TagCreateInput, TagUpdateInput } from "./types";

export async function listTags(): Promise<Tag[]> {
  const response = await api.get<Tag[]>("/tags/");
  return response.data;
}

export async function createTag(data: TagCreateInput): Promise<Tag> {
  const response = await api.post<Tag>("/tags/", data);
  return response.data;
}

export async function updateTag(tagId: string, data: TagUpdateInput): Promise<Tag> {
  const response = await api.patch<Tag>(`/tags/${tagId}`, data);
  return response.data;
}

export async function deleteTag(tagId: string): Promise<void> {
  await api.delete(`/tags/${tagId}`);
}
