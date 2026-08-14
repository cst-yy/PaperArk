import { useQuery } from "@tanstack/react-query";
import { search } from "./api";
import type { SearchMode } from "./api";

export function useSearch(query: string, page: number, pageSize = 20, mode: SearchMode = "lexical") {
  return useQuery({
    queryKey: ["search", mode, query, page, pageSize],
    queryFn: () => search(query, page, pageSize, mode),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  });
}
