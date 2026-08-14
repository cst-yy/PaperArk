import { AlertCircle, FileText } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { PDFDocumentProxy } from "pdfjs-dist";

import { useAnnotations, useCreateAnnotation, useDeleteAnnotation, useUpdateAnnotation } from "@/features/annotation/hooks";
import type { Annotation, AnnotationColor, NormalizedRect, SelectionContext, UpdateAnnotationInput } from "@/features/annotation/types";
import { getDocumentFileUrl } from "@/features/paper/api";
import { EditPaperDialog } from "@/features/paper/components/EditPaperDialog";
import { useDeletePaper, usePaper, useSetPaperReadingStatus } from "@/features/paper/hooks";
import { useReadingProgressSync } from "@/features/reading/useReadingProgressSync";
import { OutlinePanel } from "@/features/reader/components/OutlinePanel";
import { PDFViewer } from "@/features/reader/components/PDFViewer";
import { ReaderSidebar } from "@/features/reader/components/ReaderSidebar";
import { ReaderToolbar } from "@/features/reader/components/ReaderToolbar";
import { usePdfOutline } from "@/features/reader/hooks/usePdfOutline";
import { useReaderStore } from "@/stores/readerStore";

export default function Reader() {
  const { paperId } = useParams<{ paperId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: paper, isLoading, isError, error, refetch } = usePaper(paperId);
  const requestedDocumentId = searchParams.get("document_id");
  const activeDocument = paper?.documents.find((document) => document.id === requestedDocumentId)
    ?? paper?.document
    ?? paper?.documents[0];
  const documentId = activeDocument?.id;
  const reset = useReaderStore((state) => state.reset);
  const currentPage = useReaderStore((state) => state.currentPage);
  const totalPages = useReaderStore((state) => state.totalPages);
  const setCurrentPage = useReaderStore((state) => state.setCurrentPage);
  const [loadedPdf, setLoadedPdf] = useState<{ paperId: string; documentId: string; pdf: PDFDocumentProxy } | null>(null);
  const [activeAnnotation, setActiveAnnotation] = useState<{ paperId: string; id: string } | null>(null);
  const [areaModeState, setAreaModeState] = useState<{ paperId: string; enabled: boolean } | null>(null);
  const [editingPaper, setEditingPaper] = useState(false);
  const activePdf = loadedPdf && loadedPdf.paperId === paperId && loadedPdf.documentId === documentId ? loadedPdf.pdf : null;
  const activeAnnotationId = activeAnnotation && activeAnnotation.paperId === paperId ? activeAnnotation.id : null;
  const areaMode = areaModeState !== null && areaModeState.paperId === paperId && areaModeState.enabled;
  const { outline, isLoading: isOutlineLoading } = usePdfOutline(activePdf);
  const { data: annotations = [], isLoading: annotationsLoading } = useAnnotations(paperId, documentId);
  const createAnnotation = useCreateAnnotation(paperId ?? "");
  const updateAnnotation = useUpdateAnnotation(paperId ?? "");
  const deleteAnnotation = useDeleteAnnotation(paperId ?? "");
  const deletePaper = useDeletePaper();
  const setReadingStatus = useSetPaperReadingStatus();
  const progressSync = useReadingProgressSync({
    paperId,
    documentId,
    currentPage,
    totalPages,
    setCurrentPage,
  });

  useEffect(() => {
    reset();
  }, [documentId, paperId, reset]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable) return;
      const state = useReaderStore.getState();
      if (event.key === "ArrowLeft" || event.key === "PageUp") { event.preventDefault(); state.prevPage(); }
      else if (event.key === "ArrowRight" || event.key === "PageDown") { event.preventDefault(); state.nextPage(); }
      else if ((event.ctrlKey || event.metaKey) && event.key === "+") { event.preventDefault(); state.zoomIn(); }
      else if ((event.ctrlKey || event.metaKey) && event.key === "-") { event.preventDefault(); state.zoomOut(); }
      else if ((event.ctrlKey || event.metaKey) && event.key === "0") { event.preventDefault(); state.fitWidth(); }
      else if (event.key === "Escape") setAreaModeState(paperId ? { paperId, enabled: false } : null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [paperId]);

  const handleDocumentLoad = useCallback((document: PDFDocumentProxy) => {
    if (paperId && documentId) setLoadedPdf({ paperId, documentId, pdf: document });
    void progressSync.restoreAfterDocumentLoad(document);
  }, [documentId, paperId, progressSync]);

  if (isLoading) return <ReaderLoading />;
  if (isError || !paper) return <ReaderState title="论文加载失败" description={error instanceof Error ? error.message : "无法获取这篇论文的信息。"} actionLabel="重试" onAction={() => void refetch()} />;
  if (!activeDocument) return <ReaderState icon={FileText} title="暂无 PDF" description="该论文尚未关联 PDF 文件。请通过“导入 PDF”重新添加文件。" />;

  const activeDocumentId = activeDocument.id;
  const pdfUrl = getDocumentFileUrl(activeDocumentId);
  const createTextAnnotation = (selection: SelectionContext, type: "highlight" | "underline" | "comment", color: AnnotationColor) => {
    if (!paperId) return;
    createAnnotation.mutate({ paper_id: paperId, document_id: activeDocumentId, type, page_number: selection.pageNumber, selected_text: selection.text, prefix_text: selection.prefixText, suffix_text: selection.suffixText, position_data: { kind: "text", rects: selection.rects }, color });
  };
  const createAreaAnnotation = (rect: NormalizedRect) => {
    if (!paperId) return;
    setAreaModeState({ paperId, enabled: false });
    createAnnotation.mutate({ paper_id: paperId, document_id: activeDocumentId, type: "area", page_number: currentPage, position_data: { kind: "area", rect }, color: "yellow" });
  };
  const jumpToAnnotation = (annotation: Annotation) => {
    setCurrentPage(annotation.page_number);
    if (!paperId) return;
    setActiveAnnotation({ paperId, id: annotation.id });
    window.setTimeout(() => setActiveAnnotation((current) => current?.id === annotation.id ? null : current), 1100);
  };
  const updateAnnotationComment = (annotationId: string, input: UpdateAnnotationInput) => updateAnnotation.mutate({ annotationId, input });

  return <div className="flex h-screen min-h-0 flex-col overflow-hidden bg-white dark:bg-slate-900">
    <ReaderToolbar
      title={paper.title}
      readingStatus={paper.reading_status}
      isReadingStatusPending={setReadingStatus.isPending}
      onReadingStatusChange={(readingStatus) => {
        if (paperId) setReadingStatus.mutate({ paperId, readingStatus });
      }}
      onEditPaper={() => setEditingPaper(true)}
    />
    <div className="flex min-h-0 flex-1">
      <OutlinePanel items={outline} isLoading={isOutlineLoading} activePage={currentPage} onJumpToPage={setCurrentPage} />
      <PDFViewer fileUrl={pdfUrl} annotations={annotations} activeAnnotationId={activeAnnotationId} areaMode={areaMode} onDocumentLoad={handleDocumentLoad} onCreateTextAnnotation={createTextAnnotation} onCreateAreaAnnotation={createAreaAnnotation} onAnnotationClick={jumpToAnnotation} />
      <ReaderSidebar annotations={annotations} isLoading={annotationsLoading} areaMode={areaMode} onToggleAreaMode={() => paperId && setAreaModeState({ paperId, enabled: !areaMode })} onJumpTo={jumpToAnnotation} onUpdate={updateAnnotationComment} onDelete={(annotationId) => deleteAnnotation.mutate(annotationId)} />
    </div>
    {editingPaper && <EditPaperDialog paper={paper} onClose={() => setEditingPaper(false)} onDelete={async (target) => { await deletePaper.mutateAsync(target.id); navigate("/library", { replace: true }); }} />}
  </div>;
}

function ReaderLoading() { return <div className="flex h-screen items-center justify-center bg-gray-50 text-sm text-gray-500 dark:bg-slate-950 dark:text-gray-400">正在加载论文…</div>; }
function ReaderState({ icon: Icon = AlertCircle, title, description, actionLabel, onAction }: { icon?: typeof AlertCircle; title: string; description: string; actionLabel?: string; onAction?: () => void }) {
  return <div className="flex h-screen flex-col items-center justify-center bg-gray-50 p-6 text-center dark:bg-slate-950"><Icon className="h-8 w-8 text-gray-400" /><h1 className="mt-3 text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h1><p className="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">{description}</p>{actionLabel && onAction && <button type="button" className="btn-primary mt-5" onClick={onAction}>{actionLabel}</button>}</div>;
}
