import type { ColumnWidthPreference, PaperListColumn } from "./types";

export interface ColumnSpec { min: number; weight: number; max?: number; resizable?: boolean }
export const COLUMN_LAYOUT: Record<PaperListColumn, ColumnSpec> = {
  title:{min:80,weight:5,max:640},title_zh:{min:80,weight:5,max:640},abstract:{min:60,weight:5,max:640},citation_text:{min:60,weight:5,max:640},authors:{min:58,weight:3,max:360},journal:{min:52,weight:2.5,max:300},conference:{min:52,weight:2.5,max:300},publication_year:{min:48,weight:.8,max:90},doi:{min:52,weight:2.2,max:300},arxiv_id:{min:48,weight:1.8,max:240},url:{min:52,weight:2,max:300},publisher:{min:50,weight:2,max:260},citation_count:{min:44,weight:.8,max:88},keywords:{min:58,weight:3,max:320},tags:{min:50,weight:2.5,max:260},folders:{min:48,weight:2,max:240},reading_status:{min:58,weight:1.2,max:120},starred:{min:40,weight:.7,max:54,resizable:false},notes:{min:44,weight:.7,max:76},created_at:{min:52,weight:1.6,max:170},updated_at:{min:52,weight:1.6,max:170},
};
export type WidthPreferences=Partial<Record<PaperListColumn,ColumnWidthPreference>>;

export function sanitizeColumnWidths(input:WidthPreferences):WidthPreferences { const output:WidthPreferences={};for(const [id,value] of Object.entries(input)){if(!(id in COLUMN_LAYOUT)||!value)continue;const column=id as PaperListColumn,spec=COLUMN_LAYOUT[column],number=Math.round(Number(value.preferred_width));if(!Number.isFinite(number))continue;output[column]={preferred_width:clamp(number,spec.min,spec.max??800),mode:value.mode==="manual"?"manual":"auto"};}return output; }

export function calculateColumnLayout(columns:PaperListColumn[],available:number,preferences:WidthPreferences={}):Record<PaperListColumn,number>{
  const result={} as Record<PaperListColumn,number>;if(!columns.length)return result;const target=Math.max(0,Math.floor(available));const clean=sanitizeColumnWidths(preferences);
  const values=columns.map(id=>clean[id]?.mode==="manual"?clamp(clean[id]!.preferred_width,COLUMN_LAYOUT[id].min,COLUMN_LAYOUT[id].max??800):COLUMN_LAYOUT[id].min);
  let total=values.reduce((a,b)=>a+b,0);
  if(total>target){shrink(values,columns,target,columns.filter(id=>clean[id]?.mode!=="manual"));total=values.reduce((a,b)=>a+b,0);if(total>target)shrink(values,columns,target,columns);}
  total=values.reduce((a,b)=>a+b,0);if(total<target)grow(values,columns,target-total,columns.filter(id=>clean[id]?.mode!=="manual"));
  total=values.reduce((a,b)=>a+b,0);if(total<target)grow(values,columns,target-total,columns);
  const rounded=roundToTotal(values,target);columns.forEach((id,index)=>{result[id]=rounded[index];});return result;
}

export function resizeColumn(columns:PaperListColumn[],rendered:Record<PaperListColumn,number>,preferences:WidthPreferences,column:PaperListColumn,delta:number):WidthPreferences{
  const spec=COLUMN_LAYOUT[column];if(!spec||spec.resizable===false)return preferences;const desired=clamp((rendered[column]??spec.min)+delta,spec.min,spec.max??800);return {...preferences,[column]:{preferred_width:desired,mode:"manual"}};
}
export function resetColumnWidth(preferences:WidthPreferences,column:PaperListColumn):WidthPreferences{return {...preferences,[column]:{preferred_width:COLUMN_LAYOUT[column].min,mode:"auto"}};}
export function getMaximumResizeDelta(columns:PaperListColumn[],rendered:Record<PaperListColumn,number>,column:PaperListColumn):number{return columns.filter(id=>id!==column).reduce((sum,id)=>sum+Math.max(0,(rendered[id]??0)-COLUMN_LAYOUT[id].min),0);}
export function calculateAdaptiveColumns(columns:PaperListColumn[],available:number):number[]{const layout=calculateColumnLayout(columns,available);return columns.map(id=>layout[id]);}

function shrink(values:number[],columns:PaperListColumn[],target:number,candidates:PaperListColumn[]){let excess=values.reduce((a,b)=>a+b,0)-target;while(excess>.01){const active=candidates.map(id=>columns.indexOf(id)).filter(index=>index>=0&&values[index]>COLUMN_LAYOUT[columns[index]].min+.01);if(!active.length)break;const capacity=active.reduce((sum,index)=>sum+values[index]-COLUMN_LAYOUT[columns[index]].min,0);for(const index of active){const room=values[index]-COLUMN_LAYOUT[columns[index]].min;const amount=Math.min(room,excess*room/capacity);values[index]-=amount;}const next=values.reduce((a,b)=>a+b,0)-target;if(next>=excess-.01)break;excess=next;}}
function grow(values:number[],columns:PaperListColumn[],remaining:number,candidates:PaperListColumn[]){while(remaining>.01){const active=candidates.map(id=>columns.indexOf(id)).filter(index=>index>=0&&values[index]<(COLUMN_LAYOUT[columns[index]].max??Infinity)-.01);if(!active.length)break;const weight=active.reduce((sum,index)=>sum+COLUMN_LAYOUT[columns[index]].weight,0);let used=0;for(const index of active){const spec=COLUMN_LAYOUT[columns[index]],room=(spec.max??Infinity)-values[index],amount=Math.min(room,remaining*spec.weight/weight);values[index]+=amount;used+=amount;}if(used<.01)break;remaining-=used;}}
function roundToTotal(values:number[],total:number):number[]{const rounded=values.map(value=>Math.max(1,Math.floor(value)));let remainder=total-rounded.reduce((sum,value)=>sum+value,0);for(let i=0;remainder>0;i=(i+1)%rounded.length){rounded[i]++;remainder--;}for(let i=rounded.length-1;remainder<0&&i>=0;i=(i-1+rounded.length)%rounded.length){if(rounded[i]>1){rounded[i]--;remainder++;}}return rounded;}
const clamp=(value:number,min:number,max:number)=>Math.max(min,Math.min(max,value));
