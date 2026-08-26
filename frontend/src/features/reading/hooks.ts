import { useQuery } from "@tanstack/react-query";
import { getReadingProgress, getRecentReading } from "./api";

export function useReadingProgress(paperId?: string, documentId?: string) {
  return useQuery({
    queryKey: ["reading-progress", paperId, documentId],
    queryFn: () => getReadingProgress(paperId!, documentId!),
    enabled: Boolean(paperId && documentId),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}

export function useRecentReading(limit = 2) {
  return useQuery({
    queryKey: ["reading", "recent", limit],
    queryFn: () => getRecentReading(limit),
  });
}
