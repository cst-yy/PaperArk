import{api}from"@/services/api";import type{Memo,MemoCreate,MemoPatch}from"./types";
export const listMemos=async()=>(await api.get<Memo[]>("/memos/",{params:{limit:20}})).data;
export const createMemo=async(data:MemoCreate)=>(await api.post<Memo>("/memos/",data)).data;
export const updateMemo=async(id:string,data:MemoPatch)=>(await api.patch<Memo>(`/memos/${id}`,data)).data;
export const deleteMemo=async(id:string)=>{await api.delete(`/memos/${id}`);};
