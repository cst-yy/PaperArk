import { api } from "@/services/api";
import type { TranslationEstimate, TranslationJob, TranslationPage } from "./types";

export async function getTranslationPage(paperId:string,documentId:string,page:number,targetLanguage="zh-CN") {
  return (await api.get<TranslationPage>(`/papers/${paperId}/translations/page/${page}`,{params:{document_id:documentId,target_language:targetLanguage}})).data;
}
export async function estimatePageTranslation(paperId:string,documentId:string,page:number) {
  return (await api.post<TranslationEstimate>(`/papers/${paperId}/translations/estimate`,{document_id:documentId,scope_type:"page",page_number:page,target_language:"zh-CN"})).data;
}
export async function translatePage(paperId:string,documentId:string,page:number) {
  return (await api.post<TranslationJob>(`/papers/${paperId}/translations`,{document_id:documentId,scope_type:"page",page_number:page,target_language:"zh-CN",confirmed:true})).data;
}
export async function estimateTranslation(paperId:string,input:{document_id:string;scope_type:"page"|"section"|"from_page"|"paper";page_number?:number;section_id?:string;target_language:string}){return(await api.post<TranslationEstimate>(`/papers/${paperId}/translations/estimate`,input)).data;}
export async function createTranslation(paperId:string,input:{document_id:string;scope_type:"page"|"section"|"from_page"|"paper";page_number?:number;section_id?:string;target_language:string}){return(await api.post<TranslationJob>(`/papers/${paperId}/translations`,{...input,confirmed:true})).data;}
export async function editTranslationBlock(blockId:string,userTranslation:string|null,expectedRevision:number) {
  return (await api.patch<TranslationPage["translations"][number]>(`/translation-blocks/${blockId}`,{user_translation:userTranslation,expected_revision:expectedRevision})).data;
}
