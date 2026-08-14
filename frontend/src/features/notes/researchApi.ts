import { api } from "@/services/api";
import type { ResearchProfileDraft, ResearchProfileResponse } from "./researchTypes";
export async function getResearchProfile(noteId:string){return (await api.get<ResearchProfileResponse|null>(`/notes/${noteId}/research-profile`)).data;}
export async function saveResearchProfile(noteId:string,data:ResearchProfileDraft){return (await api.put<ResearchProfileResponse>(`/notes/${noteId}/research-profile`,data)).data;}
