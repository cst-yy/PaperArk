import { DEFAULT_APPEARANCE } from "./appearance";
import { COLUMN_LAYOUT } from "./columnLayout";
import type { PaperListColumn, PaperListQuery, PaperListViewSettings } from "./types";

export const PAPER_LIST_COLUMNS = Object.keys(COLUMN_LAYOUT) as PaperListColumn[];
export const DEFAULT_VISIBLE_COLUMNS: PaperListColumn[] = ["title","title_zh","authors","journal","publication_year","keywords","notes"];
export const DEFAULT_QUERY: PaperListQuery = {sort:"updated_at",order:"desc",page:1,page_size:50};
export const DEFAULT_VIEW_SETTINGS: PaperListViewSettings = {
  schema_version:2, revision:0,
  columns:{visible:DEFAULT_VISIBLE_COLUMNS,order:PAPER_LIST_COLUMNS,widths:{},layout_version:1},
  appearance:DEFAULT_APPEARANCE, query:DEFAULT_QUERY,
  layout:{filters_expanded:true,display_sections_expanded:[],last_paper_id:null,scroll_top:0},
};

export function sanitizeViewSettings(input: Partial<PaperListViewSettings> | null | undefined): PaperListViewSettings {
  const rawColumns=input?.columns;const visible=(rawColumns?.visible||DEFAULT_VISIBLE_COLUMNS).filter((x):x is PaperListColumn=>PAPER_LIST_COLUMNS.includes(x));
  const knownOrder=(rawColumns?.order||[]).filter((x):x is PaperListColumn=>PAPER_LIST_COLUMNS.includes(x));const order=[...new Set([...knownOrder,...PAPER_LIST_COLUMNS])];
  const widths:PaperListViewSettings["columns"]["widths"]={};
  for(const [key,value] of Object.entries(rawColumns?.widths||{})){if(!PAPER_LIST_COLUMNS.includes(key as PaperListColumn)||!value)continue;const spec=COLUMN_LAYOUT[key as PaperListColumn];const preferred=Math.round(Number(value.preferred_width));if(Number.isFinite(preferred))widths[key as PaperListColumn]={preferred_width:Math.max(spec.min,Math.min(spec.max??800,preferred)),mode:value.mode==="manual"?"manual":"auto"};}
  const query={...DEFAULT_QUERY,...(input?.query||{})};
  return {schema_version:2,revision:Math.max(0,Number(input?.revision)||0),columns:{visible:visible.length?visible:DEFAULT_VISIBLE_COLUMNS,order,widths,layout_version:1},appearance:{...DEFAULT_APPEARANCE,...(input?.appearance||{})},query,layout:{...DEFAULT_VIEW_SETTINGS.layout,...(input?.layout||{})}};
}

export function hasExplicitQuery(params: URLSearchParams): boolean {
  return ["q","year_from","year_to","journal","author","tag_id","keyword","reading_status","starred","sort","order","page","page_size"].some(key=>params.has(key));
}
