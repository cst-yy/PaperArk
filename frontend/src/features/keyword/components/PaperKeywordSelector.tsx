import { ChevronDown, Plus, Trash2, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { useDismissibleLayer } from "@/components/overlay";
import type { Keyword, KeywordInput } from "../types";

interface PaperKeywordSelectorProps {
  value: KeywordInput[];
  suggestions: Keyword[];
  disabled?: boolean;
  deletingKeywordId?: string | null;
  onChange: (value: KeywordInput[]) => void;
  onDeleteSuggestion: (keyword: Keyword) => void;
}

const normalized = (value: string) => value.trim().toLocaleLowerCase();

export function PaperKeywordSelector({ value, suggestions, disabled, deletingKeywordId, onChange, onDeleteSuggestion }: PaperKeywordSelectorProps) {
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const selectorRef = useRef<HTMLDivElement>(null);
  const optionsRef = useRef<HTMLDivElement>(null);
  const layerId = useDismissibleLayer({ open: isOpen, onOpenChange: setIsOpen, triggerRef: selectorRef, contentRef: optionsRef });
  const options = useMemo(() => {
    const selected = new Set(value.map((item) => normalized(item.name)));
    const query = normalized(input);
    return suggestions.filter((keyword) => !selected.has(normalized(keyword.display_name)) && (!query || normalized(keyword.display_name).includes(query))).slice(0, 10);
  }, [input, suggestions, value]);

  const add = (raw: string) => {
    const name = raw.trim();
    if (!name || value.some((item) => normalized(item.name) === normalized(name))) return;
    onChange([...value, { name }]);
    setInput("");
  };

  return <section className="space-y-3">
    <div><h3 className="text-sm font-semibold">学术关键词</h3><p className="mt-0.5 text-xs text-gray-500">描述论文主题；与用于个人组织的标签分开维护。</p></div>
    {value.length > 0 ? <div className="flex flex-wrap gap-2">{value.map((keyword) => <span key={normalized(keyword.name)} className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-xs text-violet-700 dark:bg-violet-950/40 dark:text-violet-300"><span>{keyword.name}</span><button type="button" className="rounded-full p-0.5 hover:bg-violet-100 dark:hover:bg-violet-900" disabled={disabled} aria-label={`移除关键词 ${keyword.name}`} title="移除关键词" onClick={() => onChange(value.filter((item) => normalized(item.name) !== normalized(keyword.name)))}><X className="h-3.5 w-3.5" /></button></span>)}</div> : <p className="text-xs text-gray-500">尚未选择关键词。</p>}
    <div ref={selectorRef} className="relative"><div className="flex gap-2"><div className="relative flex-1"><input className="input pr-9" value={input} disabled={disabled} aria-label="搜索或添加关键词" aria-expanded={isOpen} aria-controls={isOpen ? `${layerId}-options` : undefined} aria-haspopup="listbox" placeholder="搜索或输入关键词" onFocus={() => setIsOpen(true)} onChange={(event) => { setInput(event.target.value); setIsOpen(true); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); add(input); setIsOpen(true); } }} /><button type="button" className="absolute inset-y-0 right-0 flex w-9 items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" aria-label={isOpen ? "收起关键词列表" : "展开关键词列表"} disabled={disabled} onClick={() => setIsOpen((open) => !open)}><ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} /></button></div><button type="button" className="btn-ghost border border-gray-200" disabled={disabled || !input.trim()} onClick={() => { add(input); setIsOpen(true); }}><Plus className="h-4 w-4" />添加</button></div>{isOpen && <div ref={optionsRef} id={`${layerId}-options`} role="listbox" className="absolute z-20 mt-1 max-h-52 w-full overflow-y-auto rounded-md border border-gray-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">{options.length > 0 ? options.map((keyword) => <div key={keyword.id} className="flex items-center rounded hover:bg-gray-100 dark:hover:bg-slate-700"><button type="button" role="option" aria-selected="false" className="min-w-0 flex-1 px-2 py-1.5 text-left text-sm" disabled={disabled || deletingKeywordId === keyword.id} onClick={() => add(keyword.display_name)}>{keyword.display_name}</button><button type="button" className="m-0.5 rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40" aria-label={`删除候选关键词 ${keyword.display_name}`} title="永久删除该关键词" disabled={disabled || deletingKeywordId === keyword.id} onClick={() => onDeleteSuggestion(keyword)}><Trash2 className="h-3.5 w-3.5" /></button></div>) : <p className="px-2 py-3 text-center text-xs text-gray-500">没有可选关键词，可直接输入后添加。</p>}</div>}</div>
  </section>;
}
