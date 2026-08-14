import { Crop, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import { AnnotationPanel } from "@/features/annotation/components/AnnotationPanel";
import type { Annotation, UpdateAnnotationInput } from "@/features/annotation/types";
import { useNotes } from "@/features/notes/hooks";
import { useReaderStore } from "@/stores/readerStore";

interface Props { paperId: string; annotations: Annotation[]; isLoading: boolean; areaMode: boolean; onToggleAreaMode: () => void; onJumpTo: (annotation: Annotation) => void; onUpdate: (id: string, input: UpdateAnnotationInput) => void; onDelete: (id: string) => void; onAddToNote: (annotation: Annotation) => void }

export function ReaderSidebar({ paperId, annotations, isLoading, areaMode, onToggleAreaMode, onJumpTo, onUpdate, onDelete, onAddToNote }: Props) {
  const currentPage = useReaderStore((state) => state.currentPage);
  const notes = useNotes(paperId);
  return <aside className="hidden w-72 shrink-0 border-l border-gray-200 bg-white md:flex md:flex-col dark:border-slate-700 dark:bg-slate-900"><div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 dark:border-slate-700"><div className="flex items-center gap-1.5 text-sm font-medium"><MessageSquare className="h-4 w-4" />批注</div><button title="框选区域" onClick={onToggleAreaMode} className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs ${areaMode ? "bg-primary-100 text-primary-700" : "text-gray-500 hover:bg-gray-100"}`}><Crop className="h-3.5 w-3.5" />区域</button></div>{areaMode && <div className="border-b bg-primary-50 px-3 py-2 text-xs text-primary-700">拖动鼠标框选 Figure、Table 或 Algorithm 区域。</div>}<AnnotationPanel annotations={annotations} currentPage={currentPage} isLoading={isLoading} onJumpTo={onJumpTo} onUpdate={onUpdate} onDelete={onDelete} onAddToNote={onAddToNote} /><div className="border-t border-gray-100 p-3 dark:border-slate-700"><p className="mb-2 text-xs font-medium text-gray-500">关联笔记</p>{notes.data?.map((note) => <Link key={note.id} to={`/notes/${note.id}`} className="block truncate rounded px-2 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-slate-800">{note.title}</Link>)}{!notes.isLoading && !notes.data?.length && <p className="text-xs text-gray-400">暂无关联笔记</p>}</div></aside>;
}
