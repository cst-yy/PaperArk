import { Bot, Crop, FileText, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";

import { AIPanel } from "@/features/ai/AIPanel";
import type { AICitation, TranslationResult } from "@/features/ai/types";
import { AnnotationPanel } from "@/features/annotation/components/AnnotationPanel";
import type { Annotation, UpdateAnnotationInput } from "@/features/annotation/types";
import { useNotes } from "@/features/notes/hooks";
import { useReaderStore } from "@/stores/readerStore";

export type ReaderSideTab = "annotations" | "notes" | "ai";

interface Props {
  paperId: string;
  annotations: Annotation[];
  isLoading: boolean;
  areaMode: boolean;
  activeTab: ReaderSideTab;
  translationText: string | null;
  translationResult: TranslationResult | null;
  translationPending: boolean;
  translationError: string | null;
  onTabChange: (tab: ReaderSideTab) => void;
  onRetryTranslation: () => void;
  onOpenCitation: (citation: AICitation) => void;
  onToggleAreaMode: () => void;
  onJumpTo: (annotation: Annotation) => void;
  onUpdate: (id: string, input: UpdateAnnotationInput) => void;
  onDelete: (id: string) => void;
  onAddToNote: (annotation: Annotation) => void;
}

export function ReaderSidebar(props: Props) {
  const currentPage = useReaderStore((state) => state.currentPage);
  const notes = useNotes(props.paperId);
  return <aside className="hidden w-80 shrink-0 border-l border-gray-200 bg-white md:flex md:flex-col dark:border-slate-700 dark:bg-slate-900">
    <div className="flex border-b border-gray-100 dark:border-slate-700">
      <Tab active={props.activeTab === "annotations"} icon={MessageSquare} label="批注" onClick={() => props.onTabChange("annotations")} />
      <Tab active={props.activeTab === "notes"} icon={FileText} label="笔记" onClick={() => props.onTabChange("notes")} />
      <Tab active={props.activeTab === "ai"} icon={Bot} label="AI" onClick={() => props.onTabChange("ai")} />
    </div>
    {props.activeTab === "annotations" && <>
      <div className="flex items-center justify-end border-b border-gray-100 px-3 py-2 dark:border-slate-700"><button title="框选区域" onClick={props.onToggleAreaMode} className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs ${props.areaMode ? "bg-primary-100 text-primary-700" : "text-gray-500 hover:bg-gray-100"}`}><Crop className="h-3.5 w-3.5" />区域</button></div>
      {props.areaMode && <div className="border-b bg-primary-50 px-3 py-2 text-xs text-primary-700">拖动鼠标框选 Figure、Table 或 Algorithm 区域。</div>}
      <AnnotationPanel annotations={props.annotations} currentPage={currentPage} isLoading={props.isLoading} onJumpTo={props.onJumpTo} onUpdate={props.onUpdate} onDelete={props.onDelete} onAddToNote={props.onAddToNote} />
    </>}
    {props.activeTab === "notes" && <div className="min-h-0 flex-1 overflow-y-auto p-3">
      <p className="mb-2 text-xs font-medium text-gray-500">当前论文关联笔记</p>
      {notes.data?.map((note) => <Link key={note.id} to={`/notes/${note.id}`} className="mb-1 block truncate rounded px-2 py-2 text-xs hover:bg-gray-100 dark:hover:bg-slate-800">{note.title}</Link>)}
      {!notes.isLoading && !notes.data?.length && <p className="text-xs text-gray-400">暂无关联笔记</p>}
    </div>}
    {props.activeTab === "ai" && <AIPanel paperId={props.paperId} translationText={props.translationText} translationResult={props.translationResult} translationPending={props.translationPending} translationError={props.translationError} onRetryTranslation={props.onRetryTranslation} onOpenCitation={props.onOpenCitation} />}
  </aside>;
}

function Tab({ active, icon: Icon, label, onClick }: { active: boolean; icon: typeof Bot; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`reader-side-tab ${active ? "reader-side-tab-active" : ""}`}><Icon className="h-3.5 w-3.5" />{label}</button>;
}
