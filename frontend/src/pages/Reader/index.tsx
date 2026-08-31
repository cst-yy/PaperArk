import { AlertCircle, ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { PDFDocumentProxy } from "pdfjs-dist";

import { translateSelection } from "@/features/ai/api";
import type { AICitation, TargetLanguage, TranslationResult } from "@/features/ai/types";
import { useAnnotations, useCreateAnnotation, useDeleteAnnotation, useUpdateAnnotation } from "@/features/annotation/hooks";
import type { Annotation, AnnotationColor, AnnotationLineStyle, NormalizedRect, SelectionContext, UpdateAnnotationInput } from "@/features/annotation/types";
import { getDocumentFileUrl } from "@/features/paper/api";
import { EditPaperDialog } from "@/features/paper/components/EditPaperDialog";
import { useDeletePaper, usePaper, useParseDocument, useSetPaperReadingStatus } from "@/features/paper/hooks";
import { useReadingProgressSync } from "@/features/reading/useReadingProgressSync";
import { AddAnnotationToNoteDialog } from "@/features/notes/AddAnnotationToNoteDialog";
import { OutlinePanel } from "@/features/reader/components/OutlinePanel";
import { ParsedSectionPanel } from "@/features/reader/components/ParsedSectionPanel";
import { ParsedReferencePanel } from "@/features/reader/components/ParsedReferencePanel";
import { ParsedElementPanel } from "@/features/reader/components/ParsedElementPanel";
import { useParsedElements } from "@/features/reader/parsedElements";
import { useParsedReferences } from "@/features/reader/parsedReferences";
import { useParsedSections } from "@/features/reader/parsedSections";
import { PDFViewer } from "@/features/reader/components/PDFViewer";
import { ReaderSidebar, type ReaderDock, type ReaderSideTab, type TranslationHistoryItem } from "@/features/reader/components/ReaderSidebar";
import { ReaderToolbar } from "@/features/reader/components/ReaderToolbar";
import { usePdfOutline } from "@/features/reader/hooks/usePdfOutline";
import { useReaderStore } from "@/stores/readerStore";
import { BilingualPage } from "@/features/translation/BilingualPage";
import { useTranslatePage, useTranslationPage } from "@/features/translation/hooks";
import type { ReaderMode } from "@/features/translation/types";
import { TranslationScopeMenu } from "@/features/translation/TranslationScopeMenu";

export default function Reader() {
  const { paperId } = useParams<{ paperId: string }>();
  const [searchParams] = useSearchParams();
  return <ReaderContent key={`${paperId}:${searchParams.get("document_id") ?? ""}:${searchParams.get("page") ?? ""}`} />;
}

function ReaderContent() {
  const { paperId } = useParams<{ paperId: string }>();
  const [searchParams] = useSearchParams();
  const [initialLocation] = useState(() => {
    const pageValue = Number(searchParams.get("page"));
    return {
      documentId: searchParams.get("document_id"),
      page: Number.isInteger(pageValue) && pageValue > 0 ? pageValue : undefined,
    };
  });
  const navigate = useNavigate();
  const { data: paper, isLoading, isError, error, refetch } = usePaper(paperId);
  const requestedDocumentId = initialLocation.documentId;
  const requestedPage = initialLocation.page;
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
  const [evidenceAnnotation, setEvidenceAnnotation] = useState<Annotation | null>(null);
  const [outlineMode, setOutlineMode] = useState<"native" | "parsed" | "references" | "elements">("native");
  const [rightTab, setRightTab] = useState<ReaderSideTab>(() => (localStorage.getItem("reader.sidebar.rightTab") as ReaderSideTab) || "annotations");
  const [bottomTab, setBottomTab] = useState<ReaderSideTab>(() => (localStorage.getItem("reader.sidebar.bottomTab") as ReaderSideTab) || "notes");
  const [leftCollapsed, setLeftCollapsed] = useState(() => localStorage.getItem("reader.left.collapsed") === "true");
  const [rightWidth, setRightWidth] = useState(() => Math.min(720, Math.max(280, Number(localStorage.getItem("reader.right.width")) || 320)));
  const [bottomHeight, setBottomHeight] = useState(() => Math.min(620, Math.max(240, Number(localStorage.getItem("reader.bottom.height")) || 360)));
  const [tabDocks, setTabDocks] = useState<Record<ReaderSideTab, ReaderDock>>(() => {
    try { return { annotations: "right", notes: "bottom", ai: "right", mindmap: "right", translations: "right", ...JSON.parse(localStorage.getItem("reader.sidebar.tabDocks") ?? "{}") }; }
    catch { return { annotations: "right", notes: "bottom", ai: "right", mindmap: "right", translations: "right" }; }
  });
  const [readerMode, setReaderMode] = useState<ReaderMode>(() => (localStorage.getItem("reader.mode") as ReaderMode) || "original");
  const [splitRatio, setSplitRatio] = useState(() => Math.min(70,Math.max(30,Number(localStorage.getItem("reader.split"))||50)));
  const [translationState, setTranslationState] = useState<{ text: string | null; targetLanguage: TargetLanguage; result: TranslationResult | null; pending: boolean; error: string | null }>({ text: null, targetLanguage: "zh-CN", result: null, pending: false, error: null });
  const [translationHistory, setTranslationHistory] = useState<TranslationHistoryItem[]>([]);
  const annotationTimerRef = useRef<number>();
  const activePdf = loadedPdf && loadedPdf.paperId === paperId && loadedPdf.documentId === documentId ? loadedPdf.pdf : null;
  const activeAnnotationId = activeAnnotation && activeAnnotation.paperId === paperId ? activeAnnotation.id : null;
  const areaMode = areaModeState !== null && areaModeState.paperId === paperId && areaModeState.enabled;
  const { outline, isLoading: isOutlineLoading } = usePdfOutline(activePdf);
  const { data: parsedSections = [], isLoading: parsedSectionsLoading } = useParsedSections(documentId);
  const { data: parsedReferences = [], isLoading: parsedReferencesLoading } = useParsedReferences(documentId);
  const { data: parsedElements = [], isLoading: parsedElementsLoading } = useParsedElements(documentId);
  const { data: annotations = [], isLoading: annotationsLoading } = useAnnotations(paperId, documentId);
  const createAnnotation = useCreateAnnotation(paperId ?? "");
  const updateAnnotation = useUpdateAnnotation(paperId ?? "");
  const deleteAnnotation = useDeleteAnnotation(paperId ?? "");
  const deletePaper = useDeletePaper();
  const setReadingStatus = useSetPaperReadingStatus();
  const parseDocument = useParseDocument();
  const progressSync = useReadingProgressSync({
    paperId,
    documentId,
    currentPage,
    totalPages,
    readingStatus: paper?.reading_status,
    initialPage: requestedPage,
    setCurrentPage,
  });
  const translationPage = useTranslationPage(paperId, documentId, currentPage, readerMode !== "original");
  const translatePageMutation = useTranslatePage(paperId ?? "", documentId ?? "", currentPage);

  const changeReaderMode = (mode: ReaderMode) => { setReaderMode(mode); localStorage.setItem("reader.mode",mode); };
  const changeSideTab = (tab: ReaderSideTab) => { const dock = tabDocks[tab]; if (dock === "bottom") { setBottomTab(tab); localStorage.setItem("reader.sidebar.bottomTab", tab); } else { setRightTab(tab); localStorage.setItem("reader.sidebar.rightTab", tab); } };
  const moveTab = (tab: ReaderSideTab, dock: ReaderDock) => { const next = { ...tabDocks, [tab]: dock }; setTabDocks(next); localStorage.setItem("reader.sidebar.tabDocks", JSON.stringify(next)); if (dock === "bottom") setBottomTab(tab); else setRightTab(tab); };
  const sideTab = rightTab;
  const changeWorkspaceDock = (dock: ReaderDock) => moveTab(dock === "bottom" ? rightTab : bottomTab, dock);
  const toggleLeft = () => setLeftCollapsed((value) => { const next = !value; localStorage.setItem("reader.left.collapsed", String(next)); return next; });
  const startRightResize = (event: React.PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (pointer: PointerEvent) => { const next = Math.min(720, Math.max(280, window.innerWidth - pointer.clientX)); setRightWidth(next); localStorage.setItem("reader.right.width", String(Math.round(next))); };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  };
  const startBottomResize = (event: React.PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (pointer: PointerEvent) => { const next = Math.min(window.innerHeight * 0.72, Math.max(240, window.innerHeight - pointer.clientY)); setBottomHeight(next); localStorage.setItem("reader.bottom.height", String(Math.round(next))); };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  };
  const startResize = (event: React.PointerEvent<HTMLDivElement>) => {
    const container=event.currentTarget.parentElement;if(!container)return;
    const move=(e:PointerEvent)=>{const rect=container.getBoundingClientRect();const next=Math.min(70,Math.max(30,((e.clientX-rect.left)/rect.width)*100));setSplitRatio(next);localStorage.setItem("reader.split",String(Math.round(next)))};
    const up=()=>{window.removeEventListener("pointermove",move);window.removeEventListener("pointerup",up)};
    window.addEventListener("pointermove",move);window.addEventListener("pointerup",up);
  };

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

  useEffect(() => () => window.clearTimeout(annotationTimerRef.current), []);

  const handleDocumentLoad = useCallback((document: PDFDocumentProxy) => {
    if (paperId && documentId) setLoadedPdf({ paperId, documentId, pdf: document });
    void progressSync.restoreAfterDocumentLoad(document);
  }, [documentId, paperId, progressSync]);

  if (isLoading) return <ReaderLoading />;
  if (isError || !paper) return <ReaderState title="论文加载失败" description={error instanceof Error ? error.message : "无法获取这篇论文的信息。"} actionLabel="重试" onAction={() => void refetch()} />;
  if (!activeDocument) return <ReaderState icon={FileText} title="暂无 PDF" description="该论文尚未关联 PDF 文件。请通过“导入 PDF”重新添加文件。" />;

  const activeDocumentId = activeDocument.id;
  const pdfUrl = getDocumentFileUrl(activeDocumentId);
  const createTextAnnotation = (selection: SelectionContext, type: "highlight" | "underline" | "comment", color: AnnotationColor, lineStyle?: AnnotationLineStyle, comment?: string) => {
    if (!paperId) return;
    createAnnotation.mutate({ paper_id: paperId, document_id: activeDocumentId, type, page_number: selection.pageNumber, selected_text: selection.text, prefix_text: selection.prefixText, suffix_text: selection.suffixText, position_data: { kind: "text", rects: selection.rects }, color, line_style: type === "underline" ? lineStyle ?? "solid" : undefined, comment });
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
    window.clearTimeout(annotationTimerRef.current);
    annotationTimerRef.current = window.setTimeout(() => setActiveAnnotation((current) => current?.id === annotation.id ? null : current), 1100);
  };
  const openCommentInSidebar = (annotation: Annotation) => {
    changeSideTab("annotations");
    if (paperId) setActiveAnnotation({ paperId, id: annotation.id });
    window.clearTimeout(annotationTimerRef.current);
    window.setTimeout(() => document.getElementById(`annotation-${annotation.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
    annotationTimerRef.current = window.setTimeout(() => setActiveAnnotation((current) => current?.id === annotation.id ? null : current), 2200);
  };
  const updateAnnotationComment = (annotationId: string, input: UpdateAnnotationInput) => updateAnnotation.mutate({ annotationId, input });
  const runTranslation = async (text: string, targetLanguage: TargetLanguage) => {
    changeSideTab("translations");
    const historyId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setTranslationState({ text, targetLanguage, result: null, pending: true, error: null });
    setTranslationHistory((current) => [...current, { id: historyId, pageNumber: currentPage, sourceText: text, result: null, pending: true, error: null, createdAt: Date.now() }]);
    try {
      const result = await translateSelection({ text, targetLanguage });
      setTranslationState((current) => current.text === text ? { ...current, result, pending: false } : current);
      setTranslationHistory((current) => current.map((item) => item.id === historyId ? { ...item, result, pending: false } : item));
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "AI 服务暂时不可用，请稍后重试。";
      setTranslationState((current) => current.text === text ? { ...current, error: message, pending: false } : current);
      setTranslationHistory((current) => current.map((item) => item.id === historyId ? { ...item, pending: false, error: message } : item));
    }
  };
  const handleTranslateSelection = (text: string) => {
    const targetLanguage: TargetLanguage = /[\u4e00-\u9fff]/.test(text) ? "en" : "zh-CN";
    void runTranslation(text, targetLanguage);
  };
  const openCitation = (citation: AICitation) => {
    if (citation.source_type === "note" && citation.note_id) {
      navigate(`/notes/${citation.note_id}`);
      return;
    }
    const targetPaperId = citation.paper_id ?? paper.id;
    const params = new URLSearchParams();
    if (citation.document_id) params.set("document_id", citation.document_id);
    if (citation.page_start) params.set("page", String(citation.page_start));
    const target = `/reader/${targetPaperId}${params.size ? `?${params.toString()}` : ""}`;
    if (targetPaperId === paper.id && (!citation.document_id || citation.document_id === activeDocumentId) && citation.page_start) {
      setCurrentPage(citation.page_start);
    } else {
      navigate(target);
    }
  };

  return <div className="flex h-screen min-h-0 flex-col overflow-hidden bg-white dark:bg-slate-900">
    <ReaderToolbar
      title={paper.title}
      readingStatus={paper.reading_status}
      isReadingStatusPending={setReadingStatus.isPending}
      onReadingStatusChange={(readingStatus) => {
        if (paperId) setReadingStatus.mutate({ paperId, readingStatus });
      }}
      parseStatus={activeDocument.parse_status}
      parseError={activeDocument.parse_error}
      isParsePending={parseDocument.isPending}
      onParse={() => parseDocument.mutate(activeDocumentId)}
      onEditPaper={() => setEditingPaper(true)}
      readerMode={readerMode}
      onReaderModeChange={changeReaderMode}
      translationControls={<TranslationScopeMenu paperId={paper.id} documentId={activeDocumentId} pageNumber={currentPage} sectionId={parsedSections.find((section) => section.page_start !== null && section.page_end !== null && section.page_start <= currentPage && section.page_end >= currentPage)?.id} onStarted={() => changeReaderMode("translation")} />}
    />
    <div className="flex min-h-0 flex-1">
      <div className={`flex h-full min-h-0 shrink-0 flex-col border-r border-gray-200 bg-white transition-[width] dark:border-slate-700 dark:bg-slate-900 ${leftCollapsed ? "w-10" : "w-64"}`}>
        {leftCollapsed ? <button type="button" className="m-1 flex h-8 items-center justify-center rounded hover:bg-gray-100 dark:hover:bg-slate-800" title="展开左侧导航" onClick={toggleLeft}><ChevronRight className="h-4 w-4" /></button> : <><div className="flex bg-white p-1 dark:bg-slate-900">
          <button type="button" className={`flex-1 rounded px-2 py-1 text-xs ${outlineMode === "native" ? "bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-gray-100" : "text-gray-500"}`} onClick={() => setOutlineMode("native")}>PDF 目录</button>
          <button type="button" className={`flex-1 rounded px-2 py-1 text-xs ${outlineMode === "parsed" ? "bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-gray-100" : "text-gray-500"}`} onClick={() => setOutlineMode("parsed")}>解析结构</button>
          <button type="button" className={`flex-1 rounded px-2 py-1 text-xs ${outlineMode === "references" ? "bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-gray-100" : "text-gray-500"}`} onClick={() => setOutlineMode("references")}>参考文献</button>
          <button type="button" className={`flex-1 rounded px-2 py-1 text-xs ${outlineMode === "elements" ? "bg-gray-100 text-gray-900 dark:bg-slate-800 dark:text-gray-100" : "text-gray-500"}`} onClick={() => setOutlineMode("elements")}>图表</button>
          <button type="button" className="rounded px-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-slate-800" title="收起左侧导航" onClick={toggleLeft}><ChevronLeft className="h-4 w-4" /></button>
        </div>
        {outlineMode === "native" ? (isOutlineLoading || outline.length > 0 ? <OutlinePanel items={outline} isLoading={isOutlineLoading} activePage={currentPage} onJumpToPage={setCurrentPage} /> : parsedSections.length > 0 ? <div className="flex min-h-0 flex-1 flex-col"><p className="border-b border-gray-100 px-3 py-2 text-[11px] text-gray-500 dark:border-slate-700">PDF 无原生书签，以下显示解析结构</p><ParsedSectionPanel sections={parsedSections} isLoading={parsedSectionsLoading} activePage={currentPage} onJumpToPage={setCurrentPage} /></div> : <OutlinePanel items={outline} isLoading={false} activePage={currentPage} onJumpToPage={setCurrentPage} />) : outlineMode === "parsed" ? <ParsedSectionPanel sections={parsedSections} isLoading={parsedSectionsLoading} activePage={currentPage} onJumpToPage={setCurrentPage} /> : outlineMode === "references" ? <ParsedReferencePanel references={parsedReferences} isLoading={parsedReferencesLoading} onJumpToPage={setCurrentPage} onOpenPaper={(targetPaperId) => navigate(`/reader/${targetPaperId}`)} /> : <ParsedElementPanel elements={parsedElements} isLoading={parsedElementsLoading} onJumpToPage={setCurrentPage} />}
        </>}
      </div>
      <div className="grid min-h-0 min-w-0 flex-1 overflow-hidden" style={{ gridTemplateRows: Object.values(tabDocks).includes("bottom") ? `minmax(0, 1fr) 4px ${bottomHeight}px` : "minmax(0, 1fr)" }}>
       <div className="flex min-h-0 min-w-0 flex-1">
        {readerMode === "original" ? <PDFViewer fileUrl={pdfUrl} annotations={annotations} activeAnnotationId={activeAnnotationId} areaMode={areaMode} onDocumentLoad={handleDocumentLoad} onCreateTextAnnotation={createTextAnnotation} onCreateAreaAnnotation={createAreaAnnotation} onAnnotationClick={jumpToAnnotation} onAnnotationUpdate={updateAnnotationComment} onAnnotationDelete={(id) => deleteAnnotation.mutate(id)} onCommentOpen={openCommentInSidebar} onTranslateSelection={handleTranslateSelection} /> : readerMode === "translation" ? <div className="min-w-0 flex-1 overflow-y-auto bg-slate-100 dark:bg-slate-950"><BilingualPage data={translationPage.data} mode={readerMode} paperId={paper.id} documentId={activeDocumentId} pending={translatePageMutation.isPending} onTranslate={()=>translatePageMutation.mutate()} reparsePending={parseDocument.isPending} onReparse={()=>parseDocument.mutate(activeDocumentId)} /></div> : <div className="flex min-w-0 flex-1 max-md:flex-col">
        <div className="flex min-h-0 min-w-0" style={{flexBasis:`${splitRatio}%`}}><PDFViewer fileUrl={pdfUrl} annotations={annotations} activeAnnotationId={activeAnnotationId} areaMode={areaMode} onDocumentLoad={handleDocumentLoad} onCreateTextAnnotation={createTextAnnotation} onCreateAreaAnnotation={createAreaAnnotation} onAnnotationClick={jumpToAnnotation} onAnnotationUpdate={updateAnnotationComment} onAnnotationDelete={(id) => deleteAnnotation.mutate(id)} onCommentOpen={openCommentInSidebar} onTranslateSelection={handleTranslateSelection} /></div>
        <div role="separator" aria-label="调整原译文比例" className="w-1 shrink-0 cursor-col-resize bg-gray-200 hover:bg-primary-400 max-md:hidden dark:bg-slate-700" onPointerDown={startResize}/>
        <div className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-950"><BilingualPage data={translationPage.data} mode={readerMode} paperId={paper.id} documentId={activeDocumentId} pending={translatePageMutation.isPending} onTranslate={()=>translatePageMutation.mutate()} reparsePending={parseDocument.isPending} onReparse={()=>parseDocument.mutate(activeDocumentId)} /></div>
      </div>}
      {Object.values(tabDocks).includes("right") && <>
        <div role="separator" aria-label="调整右侧工作区宽度" className="hidden w-1 shrink-0 cursor-col-resize bg-gray-200 hover:bg-primary-400 md:block dark:bg-slate-700" onPointerDown={startRightResize} />
        <ReaderSidebar dock="right" tabs={(Object.keys(tabDocks) as ReaderSideTab[]).filter((tab) => tabDocks[tab] === "right")} width={rightWidth} height={bottomHeight} onDockChange={changeWorkspaceDock} paperId={paper.id} paperTitle={paper.title} annotations={annotations} activeAnnotationId={activeAnnotationId} isLoading={annotationsLoading} areaMode={areaMode} activeTab={sideTab} translationText={translationState.text} translationResult={translationState.result} translationPending={translationState.pending} translationError={translationState.error} translationHistory={translationHistory} onTabChange={changeSideTab} onRetryTranslation={() => { if (translationState.text) void runTranslation(translationState.text, translationState.targetLanguage); }} onOpenCitation={openCitation} onToggleAreaMode={() => paperId && setAreaModeState({ paperId, enabled: !areaMode })} onJumpTo={jumpToAnnotation} onUpdate={updateAnnotationComment} onDelete={(annotationId) => deleteAnnotation.mutate(annotationId)} onAddToNote={setEvidenceAnnotation} />
      </>}
      </div>
      {Object.values(tabDocks).includes("bottom") && <>
        <div role="separator" aria-label="调整底部工作区高度" className="h-1 cursor-row-resize bg-gray-200 hover:bg-primary-400 dark:bg-slate-700" onPointerDown={startBottomResize} />
        <ReaderSidebar dock="bottom" tabs={(Object.keys(tabDocks) as ReaderSideTab[]).filter((tab) => tabDocks[tab] === "bottom")} width={rightWidth} height={bottomHeight} onDockChange={changeWorkspaceDock} paperId={paper.id} paperTitle={paper.title} annotations={annotations} activeAnnotationId={activeAnnotationId} isLoading={annotationsLoading} areaMode={areaMode} activeTab={bottomTab} translationText={translationState.text} translationResult={translationState.result} translationPending={translationState.pending} translationError={translationState.error} translationHistory={translationHistory} onTabChange={changeSideTab} onRetryTranslation={() => { if (translationState.text) void runTranslation(translationState.text, translationState.targetLanguage); }} onOpenCitation={openCitation} onToggleAreaMode={() => paperId && setAreaModeState({ paperId, enabled: !areaMode })} onJumpTo={jumpToAnnotation} onUpdate={updateAnnotationComment} onDelete={(annotationId) => deleteAnnotation.mutate(annotationId)} onAddToNote={setEvidenceAnnotation} />
      </>}
      </div>
    </div>
    {editingPaper && <EditPaperDialog paper={paper} onClose={() => setEditingPaper(false)} onDelete={async (target) => { await deletePaper.mutateAsync(target.id); navigate("/library", { replace: true }); }} />}
    {evidenceAnnotation && <AddAnnotationToNoteDialog annotation={evidenceAnnotation} paperTitle={paper.title} onClose={() => setEvidenceAnnotation(null)} />}
  </div>;
}

function ReaderLoading() { return <div className="flex h-screen items-center justify-center bg-gray-50 text-sm text-gray-500 dark:bg-slate-950 dark:text-gray-400">正在加载论文…</div>; }
function ReaderState({ icon: Icon = AlertCircle, title, description, actionLabel, onAction }: { icon?: typeof AlertCircle; title: string; description: string; actionLabel?: string; onAction?: () => void }) {
  return <div className="flex h-screen flex-col items-center justify-center bg-gray-50 p-6 text-center dark:bg-slate-950"><Icon className="h-8 w-8 text-gray-400" /><h1 className="mt-3 text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h1><p className="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">{description}</p>{actionLabel && onAction && <button type="button" className="btn-primary mt-5" onClick={onAction}>{actionLabel}</button>}</div>;
}
