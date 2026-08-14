import { Crop, MessageSquare } from "lucide-react";

import { AnnotationPanel } from "@/features/annotation/components/AnnotationPanel";
import type { Annotation, UpdateAnnotationInput } from "@/features/annotation/types";
import { useReaderStore } from "@/stores/readerStore";

interface ReaderSidebarProps {
  annotations: Annotation[];
  isLoading: boolean;
  areaMode: boolean;
  onToggleAreaMode: () => void;
  onJumpTo: (annotation: Annotation) => void;
  onUpdate: (annotationId: string, input: UpdateAnnotationInput) => void;
  onDelete: (annotationId: string) => void;
}

export function ReaderSidebar({ annotations, isLoading, areaMode, onToggleAreaMode, onJumpTo, onUpdate, onDelete }: ReaderSidebarProps) {
  const currentPage = useReaderStore((state) => state.currentPage);

  return <aside className="hidden w-72 shrink-0 border-l border-gray-200 bg-white md:flex md:flex-col dark:border-slate-700 dark:bg-slate-900">
    <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2 dark:border-slate-700">
      <div className="flex items-center gap-1.5 text-sm font-medium text-gray-800 dark:text-gray-100"><MessageSquare className="h-4 w-4" />批注</div>
      <button type="button" title="框选 Figure / Table 区域" onClick={onToggleAreaMode} className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs ${areaMode ? "bg-primary-100 text-primary-700 dark:bg-primary-700/30 dark:text-primary-100" : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800"}`}><Crop className="h-3.5 w-3.5" />区域</button>
    </div>
    {areaMode && <div className="border-b border-primary-100 bg-primary-50 px-3 py-2 text-xs text-primary-700 dark:border-primary-700/30 dark:bg-primary-700/20 dark:text-primary-100">拖动鼠标框选 Figure、Table 或 Algorithm 区域。</div>}
    <AnnotationPanel annotations={annotations} currentPage={currentPage} isLoading={isLoading} onJumpTo={onJumpTo} onUpdate={onUpdate} onDelete={onDelete} />
  </aside>;
}
