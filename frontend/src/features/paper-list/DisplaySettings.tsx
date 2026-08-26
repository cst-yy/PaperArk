import type { PaperListAppearance } from "./appearance";
import { DEFAULT_APPEARANCE, isHexColor } from "./appearance";

const colors: [keyof PaperListAppearance, string][] = [
  ["header_background","表头背景"],["header_text","表头文字"],["row_background","普通行"],
  ["alternate_row_background","交替行"],["selected_background","选中行"],["hover_background","悬停行"],
  ["primary_text","主文字"],["secondary_text","次文字"],["border","边框"],["link","链接"],
];
export function DisplaySettings({ value, onChange, onClose, onResetWidths, onResetLayout, onResetAll }: { value: PaperListAppearance; onChange:(value:PaperListAppearance)=>void; onClose:()=>void; onResetWidths:()=>void; onResetLayout:()=>void; onResetAll:()=>void }) {
  const patch = (next: Partial<PaperListAppearance>) => onChange({...value,...next});
  return <div>
    <div className="mb-3 flex items-center justify-between"><strong className="text-sm">显示设置</strong><button onClick={onClose}>×</button></div>
    <label className="mb-2 block text-xs">字体<select className="input mt-1 w-full" value={value.font_family} onChange={(e)=>patch({font_family:e.target.value as PaperListAppearance["font_family"]})}>{["system","Arial","Helvetica","Times New Roman","Georgia","Noto Sans","Noto Serif"].map(x=><option key={x}>{x}</option>)}</select></label>
    <SettingButtons label="字号" values={[["small","小"],["normal","标准"],["large","大"]]} active={value.font_size} onSelect={(x)=>patch({font_size:x as PaperListAppearance["font_size"]})}/>
    <SettingButtons label="密度" values={[["compact","紧凑"],["normal","标准"],["relaxed","宽松"]]} active={value.density} onSelect={(x)=>patch({density:x as PaperListAppearance["density"]})}/>
    <div className="grid grid-cols-2 gap-2">{colors.map(([key,label])=><label key={key} className="flex items-center justify-between text-xs">{label}<input type="color" value={String(value[key])} onChange={(e)=>isHexColor(e.target.value)&&patch({[key]:e.target.value} as Partial<PaperListAppearance>)} /></label>)}</div>
    <div className="mt-3 grid gap-1 border-t pt-2"><button className="btn-ghost text-xs" onClick={onResetWidths}>重置当前列宽</button><button className="btn-ghost text-xs" onClick={onResetLayout}>重置列布局</button><button className="btn-ghost text-xs" onClick={()=>onChange(DEFAULT_APPEARANCE)}>重置外观</button><button className="btn-ghost text-xs text-red-600" onClick={()=>confirm("恢复全部论文列表显示、筛选、排序和分页设置？")&&onResetAll()}>重置全部 Paper List 设置</button></div>
  </div>;
}
function SettingButtons({label,values,active,onSelect}:{label:string;values:string[][];active:string;onSelect:(x:string)=>void}) { return <div className="mb-2 text-xs"><span>{label}</span><div className="mt-1 grid grid-cols-3 gap-1">{values.map(([id,text])=><button key={id} className={active===id?"rounded bg-primary-600 px-2 py-1 text-white":"rounded bg-gray-100 px-2 py-1 dark:bg-slate-800"} onClick={()=>onSelect(id)}>{text}</button>)}</div></div>; }
