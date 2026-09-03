import { memo, useCallback, useEffect, useMemo, useRef, useState, type ComponentProps } from "react";
import { ChevronLeft, ChevronRight, Minus, Plus, ScanLine } from "lucide-react";
import { Document, Page as ReactPdfPage } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";

import "@/lib/pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import type { Annotation, AnnotationLineStyle, NormalizedRect, SelectionContext, UpdateAnnotationInput } from "@/features/annotation/types";
import { AnnotationOverlayLayer } from "@/features/reader/components/AnnotationOverlayLayer";
import { SelectionToolbar } from "@/features/reader/components/SelectionToolbar";
import { useTextSelection } from "@/features/reader/hooks/useTextSelection";
import { normalizeClientRect } from "@/features/reader/utils/rects";
import { useReaderStore } from "@/stores/readerStore";

const MAX_PDF_DEVICE_PIXEL_RATIO = 1.5;

const Page = memo(function Page(props: ComponentProps<typeof ReactPdfPage>) {
  const devicePixelRatio = typeof window === "undefined"
    ? 1
    : Math.min(window.devicePixelRatio || 1, MAX_PDF_DEVICE_PIXEL_RATIO);
  return <ReactPdfPage {...props} devicePixelRatio={devicePixelRatio} />;
}, (previous, next) => (
  previous.pageNumber === next.pageNumber &&
  previous.width === next.width &&
  previous.scale === next.scale &&
  previous.renderTextLayer === next.renderTextLayer &&
  previous.renderAnnotationLayer === next.renderAnnotationLayer
));

const PAGE_LOADING = <div className="p-12 text-sm text-gray-500">正在渲染 PDF 页面…</div>;
const PAGE_ERROR = <div className="p-12 text-sm text-red-600">该页面无法渲染。</div>;
// FileResponse currently serves PDFs as a complete 200 response without HTTP
// range support. Disabling PDF.js streaming prevents some Distiller/Elsevier
// files from repeatedly restarting their first-page render while the body is
// still being consumed.
const PDF_OPTIONS = { disableStream: true };

interface PDFViewerProps {
  fileUrl: string;
  annotations: Annotation[];
  activeAnnotationId?: string | null;
  areaMode: boolean;
  onDocumentLoad: (pdf: PDFDocumentProxy) => void;
  onCreateTextAnnotation: (selection: SelectionContext, type: "highlight" | "underline" | "comment", color: "yellow" | "green" | "blue" | "red" | "purple", lineStyle?: AnnotationLineStyle, comment?: string) => void;
  onCreateAreaAnnotation: (rect: NormalizedRect) => void;
  onAnnotationClick: (annotation: Annotation) => void;
  onAnnotationUpdate: (id: string, input: UpdateAnnotationInput) => void;
  onAnnotationDelete: (id: string) => void;
  onCommentOpen: (annotation: Annotation) => void;
  onTranslateSelection: (text: string) => void;
}

export function PDFViewer({ fileUrl, annotations, activeAnnotationId, areaMode, onDocumentLoad, onCreateTextAnnotation, onCreateAreaAnnotation, onAnnotationUpdate, onAnnotationDelete, onCommentOpen, onTranslateSelection }: PDFViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [retryKey, setRetryKey] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<Uint8Array | null>(null);
  const [pdfDataKey, setPdfDataKey] = useState<string | null>(null);
  const [selection, setSelection] = useState<SelectionContext | null>(null);
  const [areaDraft, setAreaDraft] = useState<NormalizedRect | null>(null);
  const currentPage = useReaderStore((state) => state.currentPage);
  const totalPages = useReaderStore((state) => state.totalPages);
  const scale = useReaderStore((state) => state.scale);
  const zoomMode = useReaderStore((state) => state.zoomMode);
  const setTotalPages = useReaderStore((state) => state.setTotalPages);
  const prevPage = useReaderStore((state) => state.prevPage);
  const nextPage = useReaderStore((state) => state.nextPage);
  const zoomOut = useReaderStore((state) => state.zoomOut);
  const zoomIn = useReaderStore((state) => state.zoomIn);
  const fitWidth = useReaderStore((state) => state.fitWidth);
  const captureSelection = useTextSelection({ pageNumber: currentPage, pageRef, onSelection: setSelection });
  const pdfRequestKey = `${fileUrl}-${retryKey}`;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let resizeTimer: number | undefined;
    const updateWidth = () => {
      // The left sidebar animates its width. Updating Page.width for every
      // ResizeObserver callback makes PDF.js tear down and recreate the canvas
      // several times during that animation (most visible in FedLDR). Wait
      // until the layout settles, then apply one width update.
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        // clientWidth excludes a vertical scrollbar. When a fit-width page is
        // close to the viewport height, adding/removing that scrollbar changes
        // clientWidth, which in turn changes the page height and can toggle the
        // scrollbar again. Use the border-box width so the page size is not
        // coupled to its own scrollbars.
        const nextWidth = Math.round(container.getBoundingClientRect().width);
        setContainerWidth((currentWidth) => currentWidth === nextWidth ? currentWidth : nextWidth);
      }, 180);
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(container);
    return () => {
      window.clearTimeout(resizeTimer);
      observer.disconnect();
    };
  }, []);

  // Fetch the complete response before handing it to PDF.js. The document file
  // endpoint intentionally returns a regular 200 response (rather than a byte
  // range response). Passing that URL directly lets PDF.js try to stream it;
  // Chromium can repeatedly restart the first-page render for a few PDFs with
  // complex cross-reference tables. A stable Uint8Array removes that browser
  // dependent streaming path while keeping the existing ownership-protected
  // endpoint and retry behaviour.
  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    fetch(fileUrl, {
      signal: controller.signal,
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/pdf" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`PDF 请求失败（${response.status}）`);
        }
        const buffer = await response.arrayBuffer();
        if (buffer.byteLength < 5) {
          throw new Error("PDF 文件内容为空或已损坏");
        }
        return new Uint8Array(buffer);
      })
      .then((data) => {
        if (active) {
          setLoadError(null);
          setPdfData(data);
          setPdfDataKey(pdfRequestKey);
        }
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof DOMException && error.name === "AbortError")) return;
        setPdfDataKey(pdfRequestKey);
        setLoadError(error instanceof Error ? error.message : "PDF 文件无法读取。");
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [fileUrl, pdfRequestKey]);

  const handleLoadSuccess = useCallback((pdf: PDFDocumentProxy) => { setLoadError(null); setTotalPages(pdf.numPages); onDocumentLoad(pdf); }, [onDocumentLoad, setTotalPages]);
  const handleLoadError = useCallback((error: Error) => setLoadError(error.message || "PDF 文件无法读取。"), []);
  const pdfFile = useMemo(() => (
    pdfData && pdfDataKey === pdfRequestKey ? { data: pdfData } : undefined
  ), [pdfData, pdfDataKey, pdfRequestKey]);
  const visibleLoadError = pdfDataKey === pdfRequestKey ? loadError : null;
  const pageWidth = zoomMode === "fit-width" && containerWidth > 0 ? Math.max(280, containerWidth - 64) : undefined;

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!areaMode || !pageRef.current) return;
    const rect = pageRef.current.getBoundingClientRect();
    dragStartRef.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = normalizeClientRect(new DOMRect(event.clientX, event.clientY, 1, 1), rect);
    if (point) setAreaDraft({ x: point.x, y: point.y, width: 0.001, height: 0.001 });
  };
  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!areaMode || !dragStartRef.current || !pageRef.current) return;
    const pageRect = pageRef.current.getBoundingClientRect();
    const start = normalizeClientRect(new DOMRect(dragStartRef.current.x, dragStartRef.current.y, 1, 1), pageRect);
    const end = normalizeClientRect(new DOMRect(event.clientX, event.clientY, 1, 1), pageRect);
    if (!start || !end) return;
    setAreaDraft({ x: Math.min(start.x, end.x), y: Math.min(start.y, end.y), width: Math.abs(end.x - start.x), height: Math.abs(end.y - start.y) });
  };
  const handlePointerUp = () => {
    if (areaMode && areaDraft && areaDraft.width > 0.02 && areaDraft.height > 0.02) onCreateAreaAnnotation(areaDraft);
    dragStartRef.current = null;
    setAreaDraft(null);
  };

  return <div ref={containerRef} className="min-h-0 flex-1 overflow-auto bg-slate-100 p-6 dark:bg-slate-950">
    {visibleLoadError ? <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center text-center"><h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">无法加载 PDF</h2><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">文件可能不存在、已损坏，或当前无法访问。</p><button type="button" className="btn-primary mt-5" onClick={() => { setLoadError(null); setRetryKey((key) => key + 1); }}>重试</button></div> :
      <Document key={pdfRequestKey} file={pdfFile} options={PDF_OPTIONS} onLoadSuccess={handleLoadSuccess} onLoadError={handleLoadError} noData={<div className="flex min-h-full items-center justify-center text-sm text-gray-500 dark:text-gray-400">正在读取 PDF…</div>} loading={<div className="flex min-h-full items-center justify-center text-sm text-gray-500 dark:text-gray-400">正在加载 PDF…</div>} error={null}>
        <div ref={pageRef} className={`relative mx-auto w-fit rounded-sm bg-white shadow-xl ${areaMode ? "cursor-crosshair" : ""}`} onMouseUp={() => { if (!areaMode) captureSelection(); }} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp}>
          <Page pageNumber={currentPage} width={pageWidth} scale={zoomMode === "custom" ? scale : undefined} renderTextLayer renderAnnotationLayer loading={PAGE_LOADING} error={PAGE_ERROR} />
          <AnnotationOverlayLayer pageNumber={currentPage} annotations={annotations} activeAnnotationId={activeAnnotationId} onUpdate={onAnnotationUpdate} onDelete={onAnnotationDelete} onCommentOpen={onCommentOpen} />
          {areaDraft && <div className="pointer-events-none absolute border-2 border-primary-500 bg-primary-400/15" style={{ left: `${areaDraft.x * 100}%`, top: `${areaDraft.y * 100}%`, width: `${areaDraft.width * 100}%`, height: `${areaDraft.height * 100}%` }} />}
        </div>
      </Document>}
    {!loadError && <div className="pointer-events-none sticky bottom-3 z-40 -mt-11 flex justify-center">
      <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-gray-200 bg-white/95 p-1 shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
        <button type="button" title="上一页" aria-label="上一页" disabled={currentPage <= 1} onClick={prevPage} className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 disabled:opacity-30 dark:text-gray-300 dark:hover:bg-slate-800"><ChevronLeft className="h-4 w-4" /></button>
        <span className="min-w-16 text-center text-[11px] tabular-nums text-gray-600 dark:text-gray-300">{currentPage} / {totalPages || "—"}</span>
        <button type="button" title="下一页" aria-label="下一页" disabled={!totalPages || currentPage >= totalPages} onClick={nextPage} className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 disabled:opacity-30 dark:text-gray-300 dark:hover:bg-slate-800"><ChevronRight className="h-4 w-4" /></button>
        <span className="mx-1 h-5 w-px bg-gray-200 dark:bg-slate-700" />
        <button type="button" title="缩小" aria-label="缩小" onClick={zoomOut} className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800"><Minus className="h-4 w-4" /></button>
        <span className="min-w-10 text-center text-[11px] tabular-nums text-gray-600 dark:text-gray-300">{zoomMode === "fit-width" ? "适宽" : `${Math.round(scale * 100)}%`}</span>
        <button type="button" title="放大" aria-label="放大" onClick={zoomIn} className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800"><Plus className="h-4 w-4" /></button>
        <button type="button" title="适应宽度" aria-label="适应宽度" onClick={fitWidth} className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800"><ScanLine className="h-4 w-4" /></button>
      </div>
    </div>}
    {selection && <SelectionToolbar selection={selection} onCreate={(type, color, lineStyle, comment) => { onCreateTextAnnotation(selection, type, color, lineStyle, comment); setSelection(null); window.getSelection()?.removeAllRanges(); }} onTranslate={() => { onTranslateSelection(selection.text); setSelection(null); window.getSelection()?.removeAllRanges(); }} />}
  </div>;
}
