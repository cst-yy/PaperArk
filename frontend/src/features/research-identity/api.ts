import { api } from "@/services/api";

export interface ResearchIdentity { id:string; author_id:string; author_name:string; display_name:string; orcid:string|null; email:string|null }
export interface IdentityCandidate { author_id:string; name:string; orcid:string|null; affiliation:string|null; paper_count:number }
export interface MyPaperStats { total:number; first_or_co_first:number; corresponding:number; other:number }

export const getResearchIdentity = async () => (await api.get<ResearchIdentity|null>("/research-identity")).data;
export const listIdentityCandidates = async () => (await api.get<IdentityCandidate[]>("/research-identity/candidates")).data;
export interface ResearchIdentityInput {author_id:string;display_name?:string|null;orcid?:string|null;email?:string|null}
export const setResearchIdentity = async (input:string|ResearchIdentityInput) => (await api.put<ResearchIdentity>("/research-identity", typeof input==="string"?{author_id:input}:input)).data;
export const getMyPaperStats = async () => (await api.get<MyPaperStats>("/research-identity/stats")).data;
