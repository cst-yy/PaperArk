import { api } from "@/services/api";
import type { SearchPageResponse } from "./types";

export async function search(query: string, page = 1, pageSize = 20): Promise<SearchPageResponse> {
  const response = await api.get<SearchPageResponse>("/search/", {
    params: { q: query, page, page_size: pageSize },
  });
  return response.data;
}
