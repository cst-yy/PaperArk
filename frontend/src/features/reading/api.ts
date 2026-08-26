import { api } from "@/services/api";
import type { ReadingProgress, ReadingProgressUpsert, RecentReadingItem } from "./types";

export async function getReadingProgress(
  paperId: string,
  documentId: string,
): Promise<ReadingProgress | null> {
  const response = await api.get<ReadingProgress | null>(
    `/papers/${paperId}/reading-progress`,
    { params: { document_id: documentId } },
  );
  return response.data;
}

export async function upsertReadingProgress(
  paperId: string,
  payload: ReadingProgressUpsert,
): Promise<ReadingProgress> {
  const response = await api.put<ReadingProgress>(
    `/papers/${paperId}/reading-progress`,
    payload,
  );
  return response.data;
}

export async function getRecentReading(limit = 2): Promise<RecentReadingItem[]> {
  const response = await api.get<RecentReadingItem[]>("/reading/recent", {
    params: { limit },
  });
  return response.data;
}
