import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Languages, Loader2, RefreshCw } from "lucide-react";

import type { PageBlock, ReaderMode, TranslationBlock, TranslationPage } from "./types";
import { useEditTranslation, useSaveManualTranslation, useUpdatePageBlock } from "./hooks";
import { PageBlockManager, type RegionBox } from "./PageBlockManager";
import { useReaderStore } from "@/stores/readerStore";

interface Props {
  data: TranslationPage | undefined;
  mode: ReaderMode;
  paperId: string;
  documentId: string;
  pageNumber?: number;
  onTranslate: () => void;
  pending: boolean;
  onReparse: () => void;
  reparsePending: boolean;
}

export function BilingualPage({ data, mode, paperId, documentId, pageNumber: requestedPageNumber, onTranslate, pending, onReparse, reparsePending }: Props) {
  const readerPage = useReaderStore((state) => state.currentPage);
  const pageNumber = requestedPageNumber ?? data?.blocks[0]?.page_number ?? readerPage;
  const translations = useMemo(() => new Map((data?.translations ?? []).map((item) => [item.page_block_id, item])), [data]);
  const previewRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const directPointerRef = useRef<{ clientX: number; clientY: number; point: { x: number; y: number }; dragging: boolean } | null>(null);
  const suppressPageClickRef = useRef(false);
  const [managerOpen, setManagerOpen] = useState(false);
  const [selectingRegion, setSelectingRegion] = useState(false);
  const [drawnRegion, setDrawnRegion] = useState<RegionBox | null>(null);
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectingRegion) return;
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setSelectingRegion(false);
      dragStartRef.current = null;
    };
    document.addEventListener("keydown", cancel);
    return () => document.removeEventListener("keydown", cancel);
  }, [selectingRegion]);

  const pointInPreview = (event: ReactPointerEvent<HTMLDivElement>) => {
    const rect = previewRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  };
  const updateDrawnRegion = (start: { x: number; y: number }, end: { x: number; y: number }) => setDrawnRegion({
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y),
  });
  const onRegionPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    const point = pointInPreview(event);
    if (!point) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStartRef.current = point;
    setDrawnRegion({ ...point, width: 0, height: 0 });
  };
  const onRegionPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const start = dragStartRef.current;
    const point = pointInPreview(event);
    if (start && point) updateDrawnRegion(start, point);
  };
  const onRegionPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const start = dragStartRef.current;
    const point = pointInPreview(event);
    dragStartRef.current = null;
    if (!start || !point) return;
    const region = { x: Math.min(start.x, point.x), y: Math.min(start.y, point.y), width: Math.abs(point.x - start.x), height: Math.abs(point.y - start.y) };
    if (region.width < 0.01 || region.height < 0.01) {
      setDrawnRegion(null);
      return;
    }
    setDrawnRegion(region);
    setSelectingRegion(false);
    setManagerOpen(true);
  };
  const onPagePointerDownCapture = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (selectingRegion || event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest("[data-custom-region], textarea, input, [role='separator']")) return;
    const point = pointInPreview(event);
    if (!point) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    directPointerRef.current = { clientX: event.clientX, clientY: event.clientY, point, dragging: false };
  };
  const onPagePointerMoveCapture = (event: ReactPointerEvent<HTMLDivElement>) => {
    const active = directPointerRef.current;
    if (!active) return;
    if (!active.dragging && Math.hypot(event.clientX - active.clientX, event.clientY - active.clientY) < 6) return;
    active.dragging = true;
    const point = pointInPreview(event);
    if (!point) return;
    setSelectingRegion(true);
    updateDrawnRegion(active.point, point);
    event.preventDefault();
  };
  const onPagePointerUpCapture = (event: ReactPointerEvent<HTMLDivElement>) => {
    const active = directPointerRef.current;
    directPointerRef.current = null;
    if (!active?.dragging) return;
    const point = pointInPreview(event);
    if (!point) return;
    const region = { x: Math.min(active.point.x, point.x), y: Math.min(active.point.y, point.y), width: Math.abs(point.x - active.point.x), height: Math.abs(point.y - active.point.y) };
    suppressPageClickRef.current = true;
    event.preventDefault();
    event.stopPropagation();
    if (region.width < 0.01 || region.height < 0.01) {
      setSelectingRegion(false);
      setDrawnRegion(null);
      return;
    }
    setDrawnRegion(region);
    setSelectingRegion(false);
    setManagerOpen(true);
  };
  if (!data) return <div className="flex h-full items-center justify-center text-sm text-gray-400"><Loader2 className="mr-2 h-4 w-4 animate-spin" />正在读取页面分区…</div>;
  if (!data.blocks.length) return <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
    <p className="text-sm text-gray-500">当前页没有分区，可直接新建自定义分区或重新解析。</p>
    <div className="flex items-center gap-2"><PageBlockManager documentId={documentId} page={pageNumber} open={managerOpen} onOpenChange={setManagerOpen} drawnBox={drawnRegion} onClearDrawnBox={() => setDrawnRegion(null)} onRequestDraw={() => { setManagerOpen(false); setSelectingRegion(true); setDrawnRegion(null); }} /><button type="button" className="btn-ghost" disabled={reparsePending} onClick={onReparse}>{reparsePending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}重新解析</button></div>
  </div>;

  const toolbar = <div className="flex items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-2 dark:border-slate-700 dark:bg-slate-900">
    <p className="text-xs text-gray-500">{data.translations.length ? `已有 ${data.translations.length} 段译文，可点击译文继续编辑` : "本页尚无译文，可逐段人工录入或使用 AI 翻译"}</p>
    <div className="flex shrink-0 items-center gap-1"><PageBlockManager documentId={documentId} page={data.blocks[0].page_number} open={managerOpen} onOpenChange={setManagerOpen} drawnBox={drawnRegion} onClearDrawnBox={() => setDrawnRegion(null)} onRequestDraw={() => { setManagerOpen(false); setSelectingRegion(true); setDrawnRegion(null); }} /><button type="button" className="btn-primary" disabled={pending} onClick={onTranslate}>{pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Languages className="h-4 w-4" />}AI 翻译当前页</button></div>
  </div>;

  const selectionOverlay = <div className="absolute inset-0 z-50 cursor-crosshair touch-none bg-primary-500/5 select-none" onPointerDown={onRegionPointerDown} onPointerMove={onRegionPointerMove} onPointerUp={onRegionPointerUp} onPointerCancel={() => { dragStartRef.current = null; }}><div className="absolute left-1/2 top-3 -translate-x-1/2 whitespace-nowrap rounded-full bg-slate-900/85 px-3 py-1 text-[11px] text-white shadow">拖拽框选分区 · Esc 取消</div>{drawnRegion && <div className="pointer-events-none absolute border-2 border-primary-500 bg-primary-400/15" style={{ left: `${drawnRegion.x * 100}%`, top: `${drawnRegion.y * 100}%`, width: `${drawnRegion.width * 100}%`, height: `${drawnRegion.height * 100}%` }} />}</div>;

  if (mode === "paragraph" || mode === "translation") return <div className="flex min-h-full flex-col">{toolbar}{selectingRegion ? <div className="p-5"><div ref={previewRef} className="relative mx-auto aspect-[0.707] w-full max-w-3xl bg-white shadow-lg dark:bg-slate-900">{selectionOverlay}</div><p className="mt-2 text-center text-xs text-gray-400">请在页面比例画布上拖拽；完成后可继续精调坐标。</p></div> : <div className="space-y-2 overflow-y-auto p-4">{data.blocks.map((block) => <div key={block.id} className="grid gap-2 rounded-lg border border-gray-200 p-3 lg:grid-cols-2 dark:border-slate-700"><p className="text-xs leading-5 text-gray-500">{block.source_text}</p><Editable paperId={paperId} documentId={documentId} pageBlockId={block.id} translation={translations.get(block.id)} /></div>)}</div>}</div>;

  const orderedBlocks = [...data.blocks].sort((left, right) => Number(right.is_default) - Number(left.is_default));
  return <div className="min-h-full">{toolbar}<div className="p-5"><p className="mb-2 text-center text-[11px] text-gray-400">点击分区直接输入译文；切换分区或点击空白处会自动保存。拖拽空白处可新建分区。</p><div ref={previewRef} className="relative mx-auto aspect-[0.707] w-full max-w-3xl bg-white shadow-lg dark:bg-slate-900" onPointerDownCapture={onPagePointerDownCapture} onPointerMoveCapture={onPagePointerMoveCapture} onPointerUpCapture={onPagePointerUpCapture} onPointerCancel={() => { directPointerRef.current = null; }} onClick={() => setActiveRegionId(null)} onClickCapture={(event) => { if (suppressPageClickRef.current) { suppressPageClickRef.current = false; event.preventDefault(); event.stopPropagation(); } }}>{orderedBlocks.map((block) => {
    const value = translations.get(block.id);
    if (!block.bounding_box) return null;
    if (!block.is_default) return <DraggableTranslationRegion key={block.id} block={block} documentId={documentId} paperId={paperId} page={block.page_number} translation={value} active={activeRegionId === block.id} onActivate={setActiveRegionId} />;
    return <DefaultTranslationRegion key={block.id} block={block} documentId={documentId} paperId={paperId} translation={value} active={activeRegionId === block.id} onActivate={setActiveRegionId} />;
  })}{selectingRegion && selectionOverlay}</div></div></div>;
}

function DefaultTranslationRegion({ block, documentId, paperId, translation, active, onActivate }: { block: PageBlock; documentId: string; paperId: string; translation: TranslationBlock | undefined; active: boolean; onActivate: (id: string) => void }) {
  return <DraggableTranslationRegion block={block} documentId={documentId} paperId={paperId} page={block.page_number} translation={translation} active={active} onActivate={onActivate} baseLayer />;
}

function DraggableTranslationRegion({ block, documentId, paperId, page, translation, active, onActivate, baseLayer = false }: { block: PageBlock; documentId: string; paperId: string; page: number; translation: TranslationBlock | undefined; active: boolean; onActivate: (id: string) => void; baseLayer?: boolean }) {
  const update = useUpdatePageBlock(documentId, page);
  const initial = block.bounding_box ?? { x: 0, y: 0, width: 1, height: 1 };
  const [box, setBox] = useState(initial);
  const [textStyle, setTextStyle] = useState(block.text_style ?? { font_size: 12, color: "#1f2937" });
  const boxRef = useRef(initial);
  const operation = useRef<{ kind: "move" | "resize"; startX: number; startY: number; initial: RegionBox } | null>(null);

  const start = (kind: "move" | "resize", event: ReactPointerEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    operation.current = { kind, startX: event.clientX, startY: event.clientY, initial: box };
  };
  const move = (event: ReactPointerEvent<HTMLElement>) => {
    const active = operation.current;
    const pageElement = event.currentTarget.parentElement?.parentElement;
    if (!active || !pageElement) return;
    const rect = pageElement.getBoundingClientRect();
    const dx = (event.clientX - active.startX) / rect.width;
    const dy = (event.clientY - active.startY) / rect.height;
    if (active.kind === "move") {
      const next = { ...active.initial, x: Math.max(0, Math.min(1 - active.initial.width, active.initial.x + dx)), y: Math.max(0, Math.min(1 - active.initial.height, active.initial.y + dy)) };
      boxRef.current = next;
      setBox(next);
    } else {
      const next = { ...active.initial, width: Math.max(0.02, Math.min(1 - active.initial.x, active.initial.width + dx)), height: Math.max(0.02, Math.min(1 - active.initial.y, active.initial.height + dy)) };
      boxRef.current = next;
      setBox(next);
    }
  };
  const finish = (event: ReactPointerEvent<HTMLElement>) => {
    if (!operation.current) return;
    operation.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    update.mutate({ id: block.id, input: { bounding_box: boxRef.current } });
  };

  const changeStyle = (next: { font_size: number; color: string }) => { setTextStyle(next); update.mutate({ id: block.id, input: { text_style: next } }); };
  return <div data-custom-region className={`group absolute overflow-visible rounded border bg-white/95 px-1 shadow-sm dark:bg-slate-900/95 ${baseLayer ? "z-0" : active ? "z-30 border-primary-500 ring-2 ring-primary-200" : "z-10 border-primary-300"} ${active ? "border-primary-500 ring-2 ring-primary-200" : ""} ${update.isPending ? "border-amber-400" : ""}`} style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${Math.max(box.height * 100, 2)}%`, fontSize: `${textStyle.font_size}px`, color: textStyle.color, lineHeight: 1.35 }} title={block.source_text} onPointerDown={(event) => { event.stopPropagation(); onActivate(block.id); }} onClick={(event) => event.stopPropagation()}>
    <span className="absolute -top-5 left-0 flex h-5 max-w-full touch-none cursor-move items-center gap-1 rounded-t bg-primary-500 px-1.5 text-[9px] text-white shadow-sm" title="拖动调整分区位置" onPointerDown={(event) => start("move", event)} onPointerMove={move} onPointerUp={finish} onPointerCancel={() => { operation.current = null; }}><span aria-hidden="true">⠿</span><span className="truncate">{block.name}</span></span>
    {active && <div className="absolute -top-7 right-0 flex h-6 items-center gap-1 rounded bg-white px-1 shadow dark:bg-slate-800" onPointerDown={(event) => event.stopPropagation()}><select aria-label={`${block.name} 字号`} className="h-5 rounded border px-1 text-[10px] text-gray-700" value={textStyle.font_size} onChange={(event) => changeStyle({ ...textStyle, font_size: Number(event.target.value) })}>{[8,10,12,14,16,18,20,24,28,32].map((size) => <option key={size} value={size}>{size}px</option>)}</select><input aria-label={`${block.name} 文字颜色`} type="color" className="h-5 w-6 cursor-pointer border-0 bg-transparent p-0" value={textStyle.color} onChange={(event) => changeStyle({ ...textStyle, color: event.target.value })} /></div>}
    <Editable paperId={paperId} documentId={documentId} pageBlockId={block.id} translation={translation} compact />
    <span role="separator" aria-label={`调整 ${block.name} 分区大小`} className="absolute bottom-0 right-0 h-3 w-3 touch-none cursor-nwse-resize border-b-2 border-r-2 border-primary-500 bg-white/70 opacity-70 group-hover:opacity-100 dark:bg-slate-800/70" title="拖动调整分区大小" onPointerDown={(event) => start("resize", event)} onPointerMove={move} onPointerUp={finish} onPointerCancel={() => { operation.current = null; }} />
  </div>;
}

function Editable({ paperId, documentId, pageBlockId, translation, compact = false }: { paperId: string; documentId: string; pageBlockId: string; translation: TranslationBlock | undefined; compact?: boolean }) {
  const edit = useEditTranslation();
  const create = useSaveManualTranslation();
  const [draft, setDraft] = useState<string | null>(null);
  const value = translation?.effective_translation ?? "";
  const [inlineDraft, setInlineDraft] = useState(value);
  const save = () => {
    const text = draft?.trim() ?? "";
    if (!text) return;
    const options = { onSuccess: () => setDraft(null) };
    if (translation) edit.mutate({ id: translation.id, text, revision: translation.revision }, options);
    else create.mutate({ paperId, documentId, pageBlockId, text }, options);
  };
  if (compact) {
    const saveInline = () => {
      const next = inlineDraft.trim();
      if (next === value.trim()) return;
      if (translation) edit.mutate({ id: translation.id, text: next || null, revision: translation.revision });
      else if (next) create.mutate({ paperId, documentId, pageBlockId, text: next });
    };
    return <textarea value={inlineDraft} onChange={(event) => setInlineDraft(event.target.value)} onBlur={saveInline} placeholder="点击输入译文…" className="h-full min-h-full w-full resize-none overflow-auto border-0 bg-transparent p-1 text-inherit outline-none placeholder:text-gray-400 focus:bg-white/70 dark:focus:bg-slate-900/70" aria-label="分区译文" />;
  }

  if (draft !== null) return <div className="relative z-20 min-w-48 rounded bg-white p-1 shadow-lg dark:bg-slate-800"><textarea autoFocus className="input min-h-20 text-xs" value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={save} placeholder="输入人工译文…" /><p className="mt-1 text-[10px] text-gray-400">点击输入框外自动保存</p>{(edit.isError || create.isError) && <p className="mt-1 text-[10px] text-red-500">保存失败，请刷新后重试。</p>}</div>;

  if (!translation) return <button type="button" onClick={() => setDraft("")} className="w-full rounded border border-dashed border-gray-200 px-2 py-3 text-left text-xs text-gray-400 hover:border-primary-300 hover:text-primary-600 dark:border-slate-700" title="人工录入译文">人工录入译文</button>;

  return <button type="button" onClick={() => setDraft(value)} className="group flex w-full items-start justify-between text-left text-sm leading-6" title="点击编辑译文"><span>{value}</span></button>;
}
