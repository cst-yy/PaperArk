export interface Tag {
  id: string;
  name: string;
  color: string | null;
  paper_count: number;
}

export interface TagCreateInput {
  name: string;
  color?: string;
}

export interface TagUpdateInput {
  name?: string;
  color?: string | null;
}
