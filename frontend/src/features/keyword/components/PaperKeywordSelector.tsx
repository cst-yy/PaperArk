import { Plus, X } from "lucide-react";
import { useMemo, useState } from "react";

import type { KeywordInput } from "../types";

interface PaperKeywordSelectorProps {
  value: KeywordInput[];
  suggestions: string[];
  disabled?: boolean;
  onChange: (value: KeywordInput[]) => void;
}

const normalized = (value: string) => value.trim().toLocaleLowerCase();

export function PaperKeywordSelector({ value, suggestions, disabled, onChange }: PaperKeywordSelectorProps) {
  const [input, setInput] = useState("");
  const options = useMemo(() => {
    const selected = new Set(value.map((item) => normalized(item.name)));
    const query = normalized(input);
    return suggestions.filter((name) => !selected.has(normalized(name)) && (!query || normalized(name).includes(query))).slice(0, 6);
  }, [input, suggestions, value]);

  const add = (raw: string) => {
    const name = raw.trim();
    if (!name || value.some((item) => normalized(item.name) === normalized(name))) return;
    onChange([...value, { name }]);
    setInput("");
  };

  return <section className="space-y-3">
    <div><h3 className="text-sm font-semibold">学术关键词</h3><p className="mt-0.5 text-xs text-gray-500">描述论文主题；与用于个人组织的标签分开维护。</p></div>
    <div className="flex flex-wrap gap-2">{value.map((keyword) => <span key={normalized(keyword.name)} className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-xs text-violet-700"><span>{keyword.name}</span><button type="button" disabled={disabled} aria-label={`移除关键词 ${keyword.name}`} onClick={() => onChange(value.filter((item) => normalized(item.name) !== normalized(keyword.name)))}><X className="h-3.5 w-3.5" /></button></span>)}</div>
    <div className="relative"><div className="flex gap-2"><input className="input" value={input} disabled={disabled} placeholder="输入关键词后按 Enter" onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); add(input); } }} /><button type="button" className="btn-ghost border border-gray-200" disabled={disabled || !input.trim()} onClick={() => add(input)}><Plus className="h-4 w-4" />添加</button></div>{options.length > 0 && <div className="absolute z-10 mt-1 w-full rounded-md border border-gray-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">{options.map((name) => <button key={name} type="button" className="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-gray-100 dark:hover:bg-slate-700" onClick={() => add(name)}>{name}</button>)}</div>}</div>
  </section>;
}
