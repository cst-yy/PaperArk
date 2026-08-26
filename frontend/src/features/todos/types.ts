export type TodoPriority = "low" | "normal" | "high";
export interface Todo { id:string; title:string; description:string|null; completed:boolean; priority:TodoPriority; due_at:string|null; related_paper_id:string|null; related_paper_title:string|null; position:number; revision:number; completed_at:string|null; created_at:string; updated_at:string; }
export interface TodoCreate { title:string; description?:string|null; priority?:TodoPriority; due_at?:string|null; related_paper_id?:string|null; }
export type TodoPatch = Partial<Omit<TodoCreate,"description"> & {description:string|null;completed:boolean;position:number}> & {expected_revision:number};
