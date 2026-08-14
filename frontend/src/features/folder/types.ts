export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  color: string | null;
  icon: string | null;
  sort_order: number;
  paper_count: number;
  children: Folder[];
}

export interface FolderCreateInput {
  name: string;
  parent_id?: string;
  color?: string;
  icon?: string;
}
