import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export interface ParsedSection {
  id: string;
  document_id: string;
  parent_id: string | null;
  title: string;
  section_type: string | null;
  level: number;
  page_start: number | null;
  page_end: number | null;
  order_index: number;
  raw_text?: string | null;
  children: ParsedSection[];
}

async function getParsedSections(documentId: string): Promise<ParsedSection[]> {
  return (await api.get<ParsedSection[]>(`/documents/${documentId}/sections`)).data;
}

export function useParsedSections(documentId?: string) {
  return useQuery({
    queryKey: ["document-sections", documentId],
    queryFn: () => getParsedSections(documentId!),
    enabled: Boolean(documentId),
    staleTime: 60_000,
  });
}
