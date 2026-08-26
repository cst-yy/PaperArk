import { api } from "@/services/api";
import type { ResearchProfileResponse } from "@/features/notes/researchTypes";
import type { AIAnalysisApplyRequest, AIAnalysisBrief, AIAnalysisDetail, AIChatMessage, AIChatSession, AIChatTurn, DeepReadingDraft, PaperQAResponse, RetrievalMode, TargetLanguage, TranslationResult } from "./types";

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

export async function listAIAnalyses(paperId: string): Promise<AIAnalysisBrief[]> {
  return (await api.get<AIAnalysisBrief[]>(`/papers/${paperId}/ai-analyses`)).data;
}

export async function getAIAnalysis(analysisId: string): Promise<AIAnalysisDetail> {
  return (await api.get<AIAnalysisDetail>(`/ai/analyses/${analysisId}`)).data;
}

export async function deleteAIAnalysis(analysisId: string): Promise<void> {
  await api.delete(`/ai/analyses/${analysisId}`);
}

export async function applyAIAnalysis(analysisId: string, request: AIAnalysisApplyRequest): Promise<{ application_id: string; analysis_id: string; profile: ResearchProfileResponse }> {
  return (await api.post(`/ai/analyses/${analysisId}/apply`, request)).data;
}
export async function listChatSessions(paperId:string){return (await api.get<AIChatSession[]>(`/papers/${paperId}/chat-sessions`)).data;}
export async function createChatSession(paperId:string,scopeType:"page"|"paper"="paper"){return (await api.post<AIChatSession>(`/papers/${paperId}/chat-sessions`,{title:"新对话",scope_type:scopeType})).data;}
export async function listChatMessages(sessionId:string){return (await api.get<AIChatMessage[]>(`/chat-sessions/${sessionId}/messages`)).data;}
export async function sendChatMessage(sessionId:string,content:string,scopeType:"page"|"paper",pageNumber:number){return (await api.post<AIChatTurn>(`/chat-sessions/${sessionId}/messages`,{content,scope_type:scopeType,page_number:scopeType==="page"?pageNumber:undefined})).data;}
export async function saveChatMessageAsNote(messageId:string){return (await api.post(`/chat-messages/${messageId}/save-as-note`)).data;}
