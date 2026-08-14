import { useQuery } from "@tanstack/react-query";
import { listKeywords } from "./api";

export const keywordKeys = {
  all: ["keywords"] as const,
};

export function useKeywords() {
  return useQuery({ queryKey: keywordKeys.all, queryFn: listKeywords });
}
