import { api } from "@/services/api";
import type { SearchPageResponse } from "./types";

export type SearchMode = "lexical" | "semantic" | "hybrid";

export async function search(query: string, page = 1, pageSize = 20, mode: SearchMode = "lexical"): Promise<SearchPageResponse> {
  const response = await api.get<SearchPageResponse>("/search/", {
    params: { q: query, page, page_size: pageSize, mode },
  });
  return response.data;
}
