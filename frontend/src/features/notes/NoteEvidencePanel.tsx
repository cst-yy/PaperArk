import { Link2 } from "lucide-react";

import { useDetachEvidence } from "./hooks";
import type { Note } from "./types";
import { EvidenceCard } from "./EvidenceCard";

export function NoteEvidencePanel({ note }: { note: Note }) {
  const detach = useDetachEvidence();
  return <aside className="flex w-72 shrink-0 flex-col border-l border-gray-200 dark:border-slate-700">
    <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3 text-sm font-medium dark:border-slate-700"><Link2 className="h-4 w-4" />证据（{note.evidence.length}）</div>
    <div className="space-y-3 overflow-y-auto p-3">
      {note.evidence.map((evidence) => <EvidenceCard key={evidence.id} evidence={evidence} removing={detach.isPending} onRemove={() => detach.mutate({ noteId: note.id, annotationId: evidence.annotation_id })} />)}
      {!note.evidence.length && <p className="py-10 text-center text-xs text-gray-400">从 Reader 中将已保存标注添加到这篇笔记。</p>}
    </div>
  </aside>;
}
