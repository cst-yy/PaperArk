export interface Memo{id:string;content:string;color:string|null;pinned:boolean;related_paper_id:string|null;related_paper_title:string|null;revision:number;created_at:string;updated_at:string;}
export interface MemoCreate{content:string;color?:string|null;pinned?:boolean;related_paper_id?:string|null;}
export type MemoPatch=Partial<MemoCreate>&{expected_revision:number};
