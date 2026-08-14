import { api } from "@/services/api";
import type { AISummary, AIQA } from "./types";

export async function getSummary(paperId: string): Promise<AISummary> {
  const response = await api.post<AISummary>("/ai/summary", { paper_id: paperId });
  return response.data;
}

export async function askQuestion(
  paperId: string,
  question: string
): Promise<AIQA> {
  const response = await api.post<AIQA>("/ai/qa", {
    paper_id: paperId,
    question,
  });
  return response.data;
}

export async function extractConcepts(paperId: string): Promise<{
  paper_id: string;
  concepts: string[];
}> {
  const response = await api.post("/ai/concepts", { paper_id: paperId });
  return response.data;
}
