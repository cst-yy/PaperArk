import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export interface ParsedReference {
  id: string;
  document_id: string;
  section_id: string | null;
  order_index: number;
  raw_text: string;
  title: string | null;
  authors: string[] | null;
  year: number | null;
  doi: string | null;
  arxiv_id: string | null;
  venue: string | null;
  page_start: number;
  page_end: number;
  matched_paper: { id: string; title: string } | null;
  match_method: string | null;
  match_confidence: number | null;
}

async function getParsedReferences(documentId: string): Promise<ParsedReference[]> {
  return (await api.get<ParsedReference[]>(`/documents/${documentId}/references`)).data;
}

export function useParsedReferences(documentId?: string) {
  return useQuery({
    queryKey: ["document-references", documentId],
    queryFn: () => getParsedReferences(documentId!),
    enabled: Boolean(documentId),
    staleTime: 60_000,
    gcTime: 60_000,
  });
}
