import { useState } from "react";
import { FilePlus2, Link2, Loader2, X } from "lucide-react";

import type { Annotation } from "@/features/annotation/types";
import { useAttachEvidence, useCreateNote, useNotes } from "./hooks";

export function AddAnnotationToNoteDialog({ annotation, paperTitle, onClose }: { annotation: Annotation; paperTitle: string; onClose: () => void }) {
  const notes = useNotes(annotation.paper_id);
  const attach = useAttachEvidence();
  const create = useCreateNote();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const pending = attach.isPending || create.isPending;
  const add = () => selectedId && attach.mutate({ noteId: selectedId, annotationId: annotation.id }, { onSuccess: onClose });
  const createAndAdd = () => create.mutate({ paper_id: annotation.paper_id, note_type: "paper", title: `${paperTitle} 笔记`, content_markdown: "", annotation_ids: [annotation.id] }, { onSuccess: onClose });

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <div className="w-full max-w-md rounded-xl bg-white shadow-xl dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-slate-700"><div className="flex items-center gap-2 font-semibold"><Link2 className="h-4 w-4" />添加到笔记</div><button onClick={onClose} aria-label="关闭"><X className="h-4 w-4" /></button></div>
      <div className="max-h-72 overflow-y-auto p-4">
        {notes.isLoading && <Loader2 className="mx-auto h-5 w-5 animate-spin text-gray-400" />}
        {notes.data?.map((note) => <label key={note.id} className="mb-2 flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 p-3 dark:border-slate-700"><input type="radio" name="note" checked={selectedId === note.id} onChange={() => setSelectedId(note.id)} /><span><span className="block text-sm font-medium">{note.title}</span><span className="mt-1 block text-xs text-gray-400">{note.evidence.length} 条证据</span></span></label>)}
        {notes.data?.length === 0 && <p className="py-5 text-center text-sm text-gray-400">当前论文还没有笔记。</p>}
      </div>
      <div className="flex items-center justify-between border-t border-gray-200 p-4 dark:border-slate-700"><button type="button" disabled={pending} onClick={createAndAdd} className="inline-flex items-center gap-1.5 text-sm text-primary-600"><FilePlus2 className="h-4 w-4" />新建论文笔记并添加</button><button type="button" disabled={!selectedId || pending} onClick={add} className="btn-primary">添加</button></div>
      {(attach.isError || create.isError) && <p className="px-4 pb-4 text-xs text-red-500">添加失败，请重试。</p>}
    </div>
  </div>;
}
