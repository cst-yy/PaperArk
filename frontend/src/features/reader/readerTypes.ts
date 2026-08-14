export interface OutlineNode {
  id: string;
  title: string;
  pageNumber: number | null;
  children: OutlineNode[];
}

export type ZoomMode = "fit-width" | "custom";
