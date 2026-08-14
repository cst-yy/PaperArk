import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";

import type { AuthorInput } from "../types";

interface AuthorEditorProps {
  authors: AuthorInput[];
  disabled?: boolean;
  onChange: (authors: AuthorInput[]) => void;
}

const emptyAuthor = (): AuthorInput => ({ name: "", orcid: "", affiliation: "" });

export function AuthorEditor({ authors, disabled, onChange }: AuthorEditorProps) {
  const update = (index: number, field: keyof AuthorInput, value: string) => {
    onChange(authors.map((author, current) => current === index ? { ...author, [field]: value } : author));
  };
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= authors.length) return;
    const next = [...authors];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return <section className="space-y-3">
    <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">作者</h3><button type="button" className="btn-ghost inline-flex items-center gap-1 text-xs" disabled={disabled} onClick={() => onChange([...authors, emptyAuthor()])}><Plus className="h-3.5 w-3.5" />添加作者</button></div>
    {authors.length === 0 ? <p className="rounded-md border border-dashed border-gray-200 px-3 py-3 text-xs text-gray-500 dark:border-slate-700">尚未添加作者。</p> : <div className="space-y-2">
      {authors.map((author, index) => <div key={`${index}-${author.name}`} className="grid gap-2 rounded-lg border border-gray-200 p-3 dark:border-slate-700 md:grid-cols-[auto_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
        <div className="flex items-center gap-0.5"><button type="button" className="btn-ghost p-1" disabled={disabled || index === 0} aria-label="上移作者" onClick={() => move(index, -1)}><ChevronUp className="h-3.5 w-3.5" /></button><button type="button" className="btn-ghost p-1" disabled={disabled || index === authors.length - 1} aria-label="下移作者" onClick={() => move(index, 1)}><ChevronDown className="h-3.5 w-3.5" /></button></div>
        <input className="input" placeholder="姓名 *" value={author.name} disabled={disabled} onChange={(event) => update(index, "name", event.target.value)} />
        <input className="input" placeholder="ORCID（可选）" value={author.orcid ?? ""} disabled={disabled} onChange={(event) => update(index, "orcid", event.target.value)} />
        <input className="input" placeholder="机构（可选）" value={author.affiliation ?? ""} disabled={disabled} onChange={(event) => update(index, "affiliation", event.target.value)} />
        <button type="button" className="btn-ghost p-1 text-red-500" aria-label="移除作者" disabled={disabled} onClick={() => onChange(authors.filter((_, current) => current !== index))}><Trash2 className="h-4 w-4" /></button>
      </div>)}
    </div>}
  </section>;
}
