import { Edit3, Filter, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import type { Annotation, UpdateAnnotationInput } from "../types";

interface AnnotationPanelProps {
  annotations: Annotation[];
  currentPage: number;
  isLoading: boolean;
  onJumpTo: (annotation: Annotation) => void;
  onUpdate: (annotationId: string, input: UpdateAnnotationInput) => void;
  onDelete: (annotationId: string) => void;
}

export function AnnotationPanel({ annotations, currentPage, isLoading, onJumpTo, onUpdate, onDelete }: AnnotationPanelProps) {
  const [scope, setScope] = useState<"all" | "page">("all");
  const [editingId, setEditingId] = useState<string | null>(null);
  const filtered = useMemo(
    () => scope === "page" ? annotations.filter((annotation) => annotation.page_number === currentPage) : annotations,
    [annotations, currentPage, scope],
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 dark:border-slate-700">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{annotations.length} 条</span>
        <div className="flex rounded border border-gray-200 p-0.5 text-xs dark:border-slate-700">
          <button type="button" onClick={() => setScope("all")} className={scope === "all" ? "rounded bg-primary-50 px-2 py-1 text-primary-700 dark:bg-primary-700/30 dark:text-primary-100" : "px-2 py-1 text-gray-500"}>全文</button>
          <button type="button" onClick={() => setScope("page")} className={scope === "page" ? "rounded bg-primary-50 px-2 py-1 text-primary-700 dark:bg-primary-700/30 dark:text-primary-100" : "px-2 py-1 text-gray-500"}>本页</button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? <p className="text-sm text-gray-400">正在加载批注…</p> : filtered.length ? filtered.map((annotation) => (
          <AnnotationItem key={annotation.id} annotation={annotation} editing={editingId === annotation.id} onEdit={() => setEditingId(annotation.id)} onCancel={() => setEditingId(null)} onJumpTo={onJumpTo} onUpdate={(input) => { onUpdate(annotation.id, input); setEditingId(null); }} onDelete={onDelete} />
        )) : <div className="flex h-36 flex-col items-center justify-center text-center text-sm text-gray-400"><Filter className="mb-2 h-5 w-5" />暂无批注</div>}
      </div>
    </div>
  );
}

function AnnotationItem({ annotation, editing, onEdit, onCancel, onJumpTo, onUpdate, onDelete }: { annotation: Annotation; editing: boolean; onEdit: () => void; onCancel: () => void; onJumpTo: (annotation: Annotation) => void; onUpdate: (input: UpdateAnnotationInput) => void; onDelete: (id: string) => void }) {
  const [comment, setComment] = useState(annotation.comment ?? "");
  return <article className="group mb-3 rounded-lg border border-gray-100 p-3 text-left hover:border-gray-200 dark:border-slate-700 dark:hover:border-slate-600">
    <button type="button" className="w-full text-left" onClick={() => onJumpTo(annotation)}>
      <div className="mb-2 flex items-center justify-between text-xs text-gray-400"><span>第 {annotation.page_number} 页</span><span className="capitalize">{annotation.type === "area" ? "区域" : annotation.type}</span></div>
      {annotation.selected_text && <p className="line-clamp-3 text-xs leading-5 text-gray-700 dark:text-gray-200">“{annotation.selected_text}”</p>}
      {annotation.type === "area" && <p className="text-xs text-gray-500">Figure / Table 区域标记</p>}
    </button>
    {editing ? <div className="mt-2"><textarea value={comment} onChange={(event) => setComment(event.target.value)} className="input text-xs" rows={3} placeholder="写下你的理解…" /><div className="mt-2 flex justify-end gap-2"><button type="button" className="text-xs text-gray-500" onClick={onCancel}>取消</button><button type="button" className="text-xs text-primary-600" onClick={() => onUpdate({ comment })}>保存</button></div></div> : annotation.comment && <p className="mt-2 border-l-2 border-primary-300 pl-2 text-xs text-gray-600 dark:text-gray-300">{annotation.comment}</p>}
    <div className="mt-2 flex justify-end gap-2 opacity-0 transition-opacity group-hover:opacity-100"><button type="button" className="text-gray-400 hover:text-primary-600" onClick={onEdit} aria-label="编辑批注"><Edit3 className="h-3.5 w-3.5" /></button><button type="button" className="text-gray-400 hover:text-red-600" onClick={() => onDelete(annotation.id)} aria-label="删除批注"><Trash2 className="h-3.5 w-3.5" /></button></div>
  </article>;
}
