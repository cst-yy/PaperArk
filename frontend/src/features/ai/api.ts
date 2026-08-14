import { api } from "@/services/api";
import type { DeepReadingDraft, PaperQAResponse, RetrievalMode, TargetLanguage, TranslationResult } from "./types";

export async function askPaperQuestion(input: {
  paperId: string;
  query: string;
  retrievalMode?: RetrievalMode;
}): Promise<PaperQAResponse> {
  const response = await api.post<PaperQAResponse>("/ai/qa", {
    paper_id: input.paperId,
    query: input.query,
    retrieval_mode: input.retrievalMode ?? "hybrid",
    max_sources: 8,
    token_budget: 6000,
  });
  return response.data;
}

export async function translateSelection(input: {
  text: string;
  targetLanguage: TargetLanguage;
}): Promise<TranslationResult> {
  const response = await api.post<TranslationResult>("/ai/translate", {
    text: input.text,
    target_language: input.targetLanguage,
  });
  return response.data;
}

export async function generateDeepReading(paperId: string): Promise<DeepReadingDraft> {
  const response = await api.post<DeepReadingDraft>("/ai/deep-reading", {
    paper_id: paperId,
    retrieval_mode: "hybrid",
  });
  return response.data;
}
