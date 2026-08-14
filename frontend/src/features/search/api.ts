import { api } from "@/services/api";
import type { SearchResponse } from "./types";

export async function search(query: string, limit: number = 20): Promise<SearchResponse> {
  const response = await api.get<SearchResponse>("/search/", {
    params: { q: query, limit },
  });
  return response.data;
}
