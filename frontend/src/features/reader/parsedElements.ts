import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export interface ParsedElement {
  id: string;
  document_id: string;
  section_id: string | null;
  element_type: "figure" | "table";
  order_index: number;
  page_number: number;
  label: string | null;
  caption: string;
  bbox: { x: number; y: number; width: number; height: number } | null;
  confidence: number | null;
}

async function getParsedElements(documentId: string): Promise<ParsedElement[]> {
  return (await api.get<ParsedElement[]>(`/documents/${documentId}/elements`)).data;
}

export function useParsedElements(documentId?: string) {
  return useQuery({
    queryKey: ["document-elements", documentId],
    queryFn: () => getParsedElements(documentId!),
    enabled: Boolean(documentId),
    staleTime: 60_000,
    gcTime: 60_000,
  });
}
