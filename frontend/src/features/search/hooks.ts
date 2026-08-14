import { useQuery } from "@tanstack/react-query";
import { search } from "./api";

export function useSearch(query: string, page: number, pageSize = 20) {
  return useQuery({
    queryKey: ["search", query, page, pageSize],
    queryFn: () => search(query, page, pageSize),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  });
}
