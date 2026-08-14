import { api } from "@/services/api";
import type { Paper, PaperPage, PaperListParams, PaperCreateInput, PaperMetadataUpdate, PaperReadingStatus, ReplaceAuthorsRequest, ReplaceFoldersRequest, ReplaceTagsRequest } from "./types";

export async function listPapers(params: PaperListParams = {}): Promise<PaperPage> {
  const response = await api.get<PaperPage>("/papers/", { params });
  return response.data;
}

export async function getPaper(paperId: string): Promise<Paper> {
  const response = await api.get<Paper>(`/papers/${paperId}`);
  return response.data;
}

export async function createPaper(data: PaperCreateInput): Promise<Paper> {
  const response = await api.post<Paper>("/papers/", data);
  return response.data;
}

export async function updatePaper(
  paperId: string,
  data: PaperMetadataUpdate
): Promise<Paper> {
  const response = await api.patch<Paper>(`/papers/${paperId}`, data);
  return response.data;
}

export async function replacePaperMetadata(paperId: string, data: import("./types").PaperMetadataDraft): Promise<Paper> {
  return (await api.put<Paper>(`/papers/${paperId}/metadata`, data)).data;
}

export async function replacePaperAuthors(paperId: string, authors: ReplaceAuthorsRequest): Promise<Paper> {
  return (await api.put<Paper>(`/papers/${paperId}/authors`, authors)).data;
}

export async function replacePaperTags(paperId: string, tags: ReplaceTagsRequest): Promise<Paper> {
  return (await api.put<Paper>(`/papers/${paperId}/tags`, tags)).data;
}

export async function replacePaperFolders(paperId: string, folders: ReplaceFoldersRequest): Promise<Paper> {
  return (await api.put<Paper>(`/papers/${paperId}/folders`, folders)).data;
}

export async function deletePaper(paperId: string): Promise<void> {
  await api.delete(`/papers/${paperId}`);
}

export async function setPaperReadingStatus(
  paperId: string,
  readingStatus: PaperReadingStatus,
): Promise<Paper> {
  const response = await api.put<Paper>(`/papers/${paperId}/reading-status`, {
    reading_status: readingStatus,
  });
  return response.data;
}

export async function starPaper(paperId: string): Promise<{ is_starred: boolean }> {
  const response = await api.put(`/papers/${paperId}/star`);
  return response.data;
}

export async function unstarPaper(paperId: string): Promise<{ is_starred: boolean }> {
  const response = await api.delete(`/papers/${paperId}/star`);
  return response.data;
}

export async function addTagToPaper(paperId: string, tagId: string): Promise<void> {
  await api.post(`/papers/${paperId}/tags/${tagId}`);
}

export async function removeTagFromPaper(paperId: string, tagId: string): Promise<void> {
  await api.delete(`/papers/${paperId}/tags/${tagId}`);
}

export async function addPaperToFolder(paperId: string, folderId: string): Promise<void> {
  await api.post(`/papers/${paperId}/folders/${folderId}`);
}

export async function removePaperFromFolder(paperId: string, folderId: string): Promise<void> {
  await api.delete(`/papers/${paperId}/folders/${folderId}`);
}

// ── PDF Upload ──

export const MAX_PDF_SIZE_MB = 100;

/**
 * Upload a PDF file and create a Paper + Document.
 * Returns the created Paper.
 * onProgress receives 0-100 percentage.
 */
export async function uploadPaper(
  file: File,
  onProgress?: (progress: number) => void,
): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<Paper>("/papers/upload", formData, {
    // Leave Content-Type undefined: Axios adds multipart/form-data together
    // with the boundary that FastAPI needs to parse the `file` field.
    headers: { "Content-Type": undefined },
    onUploadProgress(event) {
      if (!event.total) return;
      const percent = Math.round((event.loaded * 100) / event.total);
      onProgress?.(percent);
    },
  });

  return response.data;
}

// ── Document file URL ──

/**
 * Build the URL for accessing a document's PDF file.
 * Used by PDF.js or <iframe> for inline viewing.
 */
export function getDocumentFileUrl(documentId: string): string {
  return `/api/documents/${documentId}/file`;
}
