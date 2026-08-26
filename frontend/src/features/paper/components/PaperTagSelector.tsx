import { Check, Pencil, Plus } from "lucide-react";

import type { Tag } from "@/features/tag/types";
import { getStableColor } from "@/utils";

interface PaperTagSelectorProps {
  tags: Tag[];
  selectedIds: string[];
  disabled?: boolean;
  onChange: (ids: string[]) => void;
  onCreate: () => void;
  onEdit: (tag: Tag) => void;
}

export function PaperTagSelector({ tags, selectedIds, disabled, onChange, onCreate, onEdit }: PaperTagSelectorProps) {
  const toggle = (tagId: string) => onChange(selectedIds.includes(tagId) ? selectedIds.filter((id) => id !== tagId) : [...selectedIds, tagId]);
  return <section className="space-y-3"><div className="flex items-center justify-between"><h3 className="text-sm font-semibold">标签</h3><button type="button" className="btn-ghost inline-flex items-center gap-1 text-xs" disabled={disabled} onClick={onCreate}><Plus className="h-3.5 w-3.5" />新建标签</button></div><div className="flex flex-wrap gap-2 rounded-lg border border-gray-200 p-3 dark:border-slate-700">{tags.length === 0 ? <p className="text-xs text-gray-500">暂无标签，可先新建一个。</p> : tags.map((tag) => { const selected = selectedIds.includes(tag.id); return <div key={tag.id} className="inline-flex items-center rounded-full border border-gray-200 dark:border-slate-600"><button type="button" disabled={disabled} onClick={() => toggle(tag.id)} className={`inline-flex items-center gap-1.5 rounded-l-full px-2.5 py-1 text-xs ${selected ? "text-white" : "text-gray-600 dark:text-gray-300"}`} style={selected ? { backgroundColor: tag.color || getStableColor(tag.name) } : undefined}>{selected && <Check className="h-3 w-3" />}{tag.name}</button><button type="button" aria-label={`编辑标签 ${tag.name}`} title="编辑标签" disabled={disabled} className="rounded-r-full border-l border-gray-200 px-1.5 py-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:border-slate-600 dark:hover:bg-slate-700 dark:hover:text-gray-200" onClick={() => onEdit(tag)}><Pencil className="h-3 w-3" /></button></div>; })}</div></section>;
}
