import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Boxes, Loader2, MousePointer2, Plus, Save, Search, Trash2, X } from "lucide-react";

import { useDismissibleLayer } from "../../components/overlay";
import type { PageBlock } from "./types";
import { useCreatePageBlock, useDeletePageBlock, usePageBlocks, useUpdatePageBlock } from "./hooks";

export interface RegionBox { x: number; y: number; width: number; height: number }

interface Props {
  documentId: string;
  page: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  drawnBox: RegionBox | null;
  onClearDrawnBox: () => void;
  onRequestDraw: () => void;
}

export function PageBlockManager({ documentId, page, open, onOpenChange, drawnBox, onClearDrawnBox, onRequestDraw }: Props) {
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: 12, top: 56, width: 512, maxHeight: 560 });
  const blocks = usePageBlocks(documentId, page, query);
  const layerId = useDismissibleLayer({
    open,
    onOpenChange: (next) => onOpenChange(next),
    triggerRef,
    contentRef,
    group: "reader-page-blocks",
  });

  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const margin = 12;
      const width = Math.min(512, window.innerWidth - margin * 2);
      const left = Math.max(margin, Math.min(rect.right - width, window.innerWidth - width - margin));
      const roomBelow = window.innerHeight - rect.bottom - margin * 2;
      const roomAbove = rect.top - margin * 2;
      const placeAbove = roomBelow < 320 && roomAbove > roomBelow;
      const maxHeight = Math.max(240, Math.min(560, placeAbove ? roomAbove : roomBelow));
      const top = placeAbove ? Math.max(margin, rect.top - maxHeight - 8) : rect.bottom + 8;
      setPosition({ left, top, width, maxHeight });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  return <div ref={triggerRef} className="relative">
    <button type="button" className="btn-ghost inline-flex items-center gap-1 text-xs" aria-expanded={open} aria-controls={open ? `${layerId}-content` : undefined} aria-haspopup="dialog" onClick={() => onOpenChange(!open)}><Boxes className="h-3.5 w-3.5" />分区管理</button>
    {open && createPortal(<div ref={contentRef} id={`${layerId}-content`} role="dialog" aria-label={`第 ${page} 页分区管理`} className="fixed z-[120] flex flex-col rounded-xl border border-gray-200 bg-white p-3 shadow-2xl dark:border-slate-700 dark:bg-slate-900" style={{ left: position.left, top: position.top, width: position.width, maxHeight: position.maxHeight }}>
      <div className="flex shrink-0 items-start justify-between gap-3"><div><p className="text-sm font-semibold">第 {page} 页分区</p><p className="text-[11px] text-gray-400">默认保留整页分区；自定义分区可在页面上拖拽框选。</p></div><button type="button" className="rounded p-1 hover:bg-gray-100 dark:hover:bg-slate-800" aria-label="关闭" onClick={() => onOpenChange(false)}><X className="h-4 w-4" /></button></div>
      <div className="mt-3 flex shrink-0 gap-2"><label className="relative min-w-0 flex-1"><Search className="absolute left-2 top-2 h-3.5 w-3.5 text-gray-400" /><input className="input h-8 pl-7 text-xs" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="按分区名称查询…" /></label><button type="button" className="btn-primary h-8 text-xs" onClick={() => { onClearDrawnBox(); setCreating(true); }}><Plus className="h-3.5 w-3.5" />新增</button></div>
      <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain pr-1">
        {(creating || drawnBox) && <RegionEditor key={drawnBox ? `${drawnBox.x}-${drawnBox.y}-${drawnBox.width}-${drawnBox.height}` : "new"} documentId={documentId} page={page} drawnBox={drawnBox} onRequestDraw={onRequestDraw} onDone={() => { setCreating(false); onClearDrawnBox(); }} />}
        {blocks.isLoading && <Loader2 className="mx-auto my-6 h-4 w-4 animate-spin" />}
        {blocks.data?.map((block) => <RegionRow key={block.id} documentId={documentId} page={page} block={block} drawnBox={editingBlockId === block.id ? drawnBox : null} autoEdit={editingBlockId === block.id} onRequestDraw={() => { setEditingBlockId(block.id); onRequestDraw(); }} onEditDone={() => { setEditingBlockId(null); onClearDrawnBox(); }} />)}
        {!blocks.isLoading && !blocks.data?.length && <p className="py-6 text-center text-xs text-gray-400">没有匹配的分区</p>}
      </div>
    </div>, document.body)}
  </div>;
}

function RegionEditor({ documentId, page, drawnBox, onRequestDraw, onDone }: { documentId: string; page: number; drawnBox: RegionBox | null; onRequestDraw: () => void; onDone: () => void }) {
  const create = useCreatePageBlock(documentId, page);
  const [name, setName] = useState("自定义分区");
  const [box, setBox] = useState(() => drawnBox ? { x: drawnBox.x * 100, y: drawnBox.y * 100, width: drawnBox.width * 100, height: drawnBox.height * 100 } : { x: 10, y: 10, width: 80, height: 25 });
  const validBox = isValidBox(box);
  const save = () => create.mutate({ name: name.trim(), boundingBox: { x: box.x / 100, y: box.y / 100, width: box.width / 100, height: box.height / 100 } }, { onSuccess: onDone });
  return <div className="rounded-lg border border-primary-200 bg-primary-50/50 p-3 dark:border-primary-800 dark:bg-primary-950/20"><input className="input h-8 text-xs" value={name} maxLength={255} onChange={(event) => setName(event.target.value)} aria-label="分区名称" /><button type="button" className="btn-ghost mt-2 w-full justify-center border border-dashed border-primary-300 text-xs text-primary-600" onClick={onRequestDraw}><MousePointer2 className="h-3.5 w-3.5" />在页面预览上拖拽框选</button><BBoxFields value={box} onChange={setBox} />{!validBox && <p className="mt-1 text-[10px] text-amber-600">分区须位于页面内，且宽高必须大于 0。</p>}<div className="mt-2 flex justify-end gap-1"><button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={onDone}>取消</button><button type="button" className="btn-primary px-2 py-1 text-xs" disabled={!name.trim() || !validBox || create.isPending} onClick={save}>{create.isPending ? "保存中…" : "保存分区"}</button></div>{create.isError && <p className="mt-1 text-xs text-red-500">保存失败，请检查区域没有超出页面。</p>}</div>;
}

function RegionRow({ documentId, page, block, drawnBox, autoEdit, onRequestDraw, onEditDone }: { documentId: string; page: number; block: PageBlock; drawnBox: RegionBox | null; autoEdit: boolean; onRequestDraw: () => void; onEditDone: () => void }) {
  const update = useUpdatePageBlock(documentId, page);
  const remove = useDeletePageBlock(documentId, page);
  const [editing, setEditing] = useState(autoEdit);
  const [name, setName] = useState(block.name);
  const source = block.bounding_box ?? { x: 0, y: 0, width: 1, height: 1 };
  const [box, setBox] = useState(() => drawnBox ? { x: drawnBox.x * 100, y: drawnBox.y * 100, width: drawnBox.width * 100, height: drawnBox.height * 100 } : { x: source.x * 100, y: source.y * 100, width: source.width * 100, height: source.height * 100 });
  const validBox = isValidBox(box);
  const finish = () => { setEditing(false); onEditDone(); };
  const save = () => update.mutate({ id: block.id, input: { name: name.trim(), bounding_box: { x: box.x / 100, y: box.y / 100, width: box.width / 100, height: box.height / 100 } } }, { onSuccess: finish });
  if (editing) return <div className="rounded-lg border border-gray-200 p-3 dark:border-slate-700"><input className="input h-8 text-xs" value={name} maxLength={255} onChange={(event) => setName(event.target.value)} onBlur={save} /><button type="button" className="btn-ghost mt-2 w-full justify-center border border-dashed border-primary-300 text-xs text-primary-600" onClick={onRequestDraw}><MousePointer2 className="h-3.5 w-3.5" />重新拖拽框选</button><BBoxFields value={box} onChange={setBox} />{!validBox && <p className="mt-1 text-[10px] text-amber-600">分区须位于页面内，且宽高必须大于 0。</p>}<div className="mt-2 flex justify-end gap-1"><button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={finish}>关闭</button><button type="button" className="btn-primary px-2 py-1 text-xs" disabled={!name.trim() || !validBox || update.isPending} onClick={save}><Save className="h-3 w-3" />立即保存</button></div></div>;
  return <div className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2 dark:border-slate-800"><button type="button" className="min-w-0 flex-1 text-left" onClick={() => setEditing(true)}><span className="block truncate text-xs font-medium">{block.name}</span><span className="text-[10px] text-gray-400">{block.is_default ? "整页分区（可调整）" : `x ${box.x.toFixed(0)}% · y ${box.y.toFixed(0)}% · ${box.width.toFixed(0)}% × ${box.height.toFixed(0)}%`}</span></button><button type="button" className="rounded p-1 text-red-500 hover:bg-red-50" disabled={remove.isPending} onClick={() => window.confirm(`删除分区“${block.name}”？其关联译文也会删除。`) && remove.mutate(block.id)} aria-label={`删除 ${block.name}`}><Trash2 className="h-3.5 w-3.5" /></button></div>;
}

function BBoxFields({ value, onChange }: { value: RegionBox; onChange: (value: RegionBox) => void }) {
  return <div className="mt-2 grid grid-cols-4 gap-1">{(["x", "y", "width", "height"] as const).map((key) => <label key={key} className="text-[10px] text-gray-400"><span>{key === "width" ? "宽" : key === "height" ? "高" : key.toUpperCase()} %</span><input type="number" min={0} max={100} step={1} className="input mt-0.5 h-7 px-1 text-xs" value={Number(value[key].toFixed(1))} onChange={(event) => onChange({ ...value, [key]: Number(event.target.value) })} /></label>)}</div>;
}

function isValidBox(box: RegionBox) {
  return box.x >= 0 && box.y >= 0 && box.width > 0 && box.height > 0 && box.x + box.width <= 100 && box.y + box.height <= 100;
}
