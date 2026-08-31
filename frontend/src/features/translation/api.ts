import { api } from "@/services/api";
import type { PageBlock, TranslationEstimate, TranslationJob, TranslationPage } from "./types";

export type PageBlockBBox = {x:number;y:number;width:number;height:number};

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
export async function saveManualTranslationBlock(paperId:string,documentId:string,pageBlockId:string,userTranslation:string,expectedRevision?:number) {
  return (await api.put<TranslationPage["translations"][number]>(`/papers/${paperId}/translations/manual-block`,{
    document_id:documentId,page_block_id:pageBlockId,target_language:"zh-CN",user_translation:userTranslation,expected_revision:expectedRevision,
  })).data;
}
export async function listPageBlocks(documentId:string,page:number,q?:string) {
  return (await api.get<PageBlock[]>(`/documents/${documentId}/page-blocks`,{params:{page_number:page,q:q||undefined}})).data;
}
export async function createPageBlock(documentId:string,page:number,name:string,boundingBox:PageBlockBBox) {
  return (await api.post<PageBlock>(`/documents/${documentId}/page-blocks`,{page_number:page,name,bounding_box:boundingBox})).data;
}
export async function updatePageBlock(blockId:string,input:{name?:string;bounding_box?:PageBlockBBox;text_style?:{font_size:number;color:string}}) {
  return (await api.patch<PageBlock>(`/documents/page-blocks/${blockId}`,input)).data;
}
export async function deletePageBlock(blockId:string) { await api.delete(`/documents/page-blocks/${blockId}`); }
