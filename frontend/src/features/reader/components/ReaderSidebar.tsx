import { ArrowLeft, Bot, BrainCircuit, Crop, FilePlus2, FileText, Languages, Loader2, MessageSquare, PanelBottom, PanelRight, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import { AIPanel } from "@/features/ai/AIPanel";
import type { AICitation, TranslationResult } from "@/features/ai/types";
import { AnnotationPanel } from "@/features/annotation/components/AnnotationPanel";
import type { Annotation, UpdateAnnotationInput } from "@/features/annotation/types";
import { useCreateNote, useNote, useNotes, useSaveNote } from "@/features/notes/hooks";
import type { Note } from "@/features/notes/types";
import type { CanvasEdge, CanvasNode } from "@/features/graph/GraphCanvas";
import { MindMapFlowCanvas } from "@/features/graph/MindMapFlowCanvas";
import { useCreateMindMapEdge, useCreateMindMapNode, useDeleteMindMapEdge, useDeleteMindMapNode, useGraphLayout, useMindMap, useSaveGraphLayout, useUpdateMindMapEdge, useUpdateMindMapNode } from "@/features/graph/hooks";
import type { Point } from "@/features/graph/types";
import { useReaderStore } from "@/stores/readerStore";
import { api } from "@/services/api";

export type ReaderSideTab = "annotations" | "notes" | "ai" | "mindmap" | "translations";
export type ReaderDock = "right" | "bottom";

interface Props {
  paperId: string;
  paperTitle: string;
  annotations: Annotation[];
  activeAnnotationId?: string | null;
  isLoading: boolean;
  areaMode: boolean;
  activeTab: ReaderSideTab;
  translationText: string | null;
  translationResult: TranslationResult | null;
  translationPending: boolean;
  translationError: string | null;
  translationHistory: TranslationHistoryItem[];
  onTabChange: (tab: ReaderSideTab) => void;
  onRetryTranslation: () => void;
  onOpenCitation: (citation: AICitation) => void;
  onToggleAreaMode: () => void;
  onJumpTo: (annotation: Annotation) => void;
  onUpdate: (id: string, input: UpdateAnnotationInput) => void;
  onDelete: (id: string) => void;
  onAddToNote: (annotation: Annotation) => void;
  width: number;
  height: number;
  dock: ReaderDock;
  onDockChange: (dock: ReaderDock) => void;
  tabs?: ReaderSideTab[];
  onMoveTab?: (tab: ReaderSideTab, dock: ReaderDock) => void;
}

export interface TranslationHistoryItem { id: string; pageNumber: number; sourceText: string; result: TranslationResult | null; pending: boolean; error: string | null; createdAt: number; }
const TAB_META = { annotations: { icon: MessageSquare, label: "批注" }, notes: { icon: FileText, label: "笔记" }, ai: { icon: Bot, label: "AI" }, mindmap: { icon: BrainCircuit, label: "导图" }, translations: { icon: Languages, label: "翻译" } } as const;
const DEFAULT_TAB_ORDER: ReaderSideTab[] = ["annotations", "notes", "ai", "mindmap", "translations"];

export function ReaderSidebar(props: Props) {
  const currentPage = useReaderStore((state) => state.currentPage);
  const notes = useNotes(props.paperId);
  const createNote = useCreateNote();
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [draggedTab, setDraggedTab] = useState<ReaderSideTab | null>(null);
  const [tabOrder, setTabOrder] = useState<ReaderSideTab[]>(() => {
    try { const saved = JSON.parse(localStorage.getItem("reader.sidebar.tabOrder") ?? "[]") as ReaderSideTab[]; return saved.length === DEFAULT_TAB_ORDER.length && DEFAULT_TAB_ORDER.every((tab) => saved.includes(tab)) ? saved : DEFAULT_TAB_ORDER; } catch { return DEFAULT_TAB_ORDER; }
  });
  const selectedNote = useNote(selectedNoteId ?? undefined);
  const createPaperNote = () => createNote.mutate({
    paper_id: props.paperId,
    note_type: "paper",
    title: `${props.paperTitle} · 第 ${currentPage} 页笔记`.slice(0, 500),
    content_markdown: `## 第 ${currentPage} 页\n\n`,
  }, {
    onSuccess: (note) => setSelectedNoteId(note.id),
  });
  const reorder = (target: ReaderSideTab) => {
    if (!draggedTab || draggedTab === target) return;
    const next = tabOrder.filter((tab) => tab !== draggedTab);
    next.splice(next.indexOf(target), 0, draggedTab);
    setTabOrder(next); localStorage.setItem("reader.sidebar.tabOrder", JSON.stringify(next)); setDraggedTab(null);
  };
  const visibleTabs = tabOrder.filter((tab) => props.tabs ? props.tabs.includes(tab) : props.dock === "bottom" ? tab === "notes" : tab !== "notes");
  const activeTab = visibleTabs.includes(props.activeTab) ? props.activeTab : visibleTabs[0];
  return <aside className={`shrink-0 bg-white dark:bg-slate-900 ${props.dock === "right" ? "hidden border-l border-gray-200 md:flex md:flex-col dark:border-slate-700" : "flex w-full flex-col border-t border-gray-200 dark:border-slate-700"}`} style={props.dock === "right" ? { width: props.width } : { height: props.height }}>
    <div className="flex border-b border-gray-100 dark:border-slate-700">
      <div className="flex min-w-0 flex-1">{visibleTabs.map((tab) => <Tab key={tab} active={activeTab === tab} icon={tab === "translations" ? undefined : TAB_META[tab].icon} label={TAB_META[tab].label} title={tab === "translations" ? "翻译记录" : undefined} onClick={() => props.onTabChange(tab)} onDragStart={() => setDraggedTab(tab)} onDrop={() => reorder(tab)} />)}</div>
      <div className="flex shrink-0 items-center gap-0.5 px-1">
        <button type="button" title="将当前选项卡停靠到右侧" aria-pressed={props.dock === "right"} onClick={() => props.onMoveTab ? props.onMoveTab(props.activeTab, "right") : props.onDockChange("right")} className={`rounded p-1.5 ${props.dock === "right" ? "bg-primary-50 text-primary-600" : "text-gray-400 hover:bg-gray-100"}`}><PanelRight className="h-3.5 w-3.5" /></button>
        <button type="button" title="将当前选项卡停靠到底部" aria-pressed={props.dock === "bottom"} onClick={() => props.onMoveTab ? props.onMoveTab(props.activeTab, "bottom") : props.onDockChange("bottom")} className={`rounded p-1.5 ${props.dock === "bottom" ? "bg-primary-50 text-primary-600" : "text-gray-400 hover:bg-gray-100"}`}><PanelBottom className="h-3.5 w-3.5" /></button>
      </div>
    </div>
    {activeTab === "annotations" && <>
      <div className="flex items-center justify-end border-b border-gray-100 px-3 py-2 dark:border-slate-700"><button title="框选区域" onClick={props.onToggleAreaMode} className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs ${props.areaMode ? "bg-primary-100 text-primary-700" : "text-gray-500 hover:bg-gray-100"}`}><Crop className="h-3.5 w-3.5" />区域</button></div>
      {props.areaMode && <div className="border-b bg-primary-50 px-3 py-2 text-xs text-primary-700">拖动鼠标框选 Figure、Table 或 Algorithm 区域。</div>}
      <AnnotationPanel annotations={props.annotations} activeAnnotationId={props.activeAnnotationId} currentPage={currentPage} isLoading={props.isLoading} onJumpTo={props.onJumpTo} onUpdate={props.onUpdate} onDelete={props.onDelete} onAddToNote={props.onAddToNote} />
    </>}
    {activeTab === "notes" && <div className="min-h-0 flex-1 overflow-y-auto p-3">
      {selectedNoteId ? <>
        <button type="button" className="mb-2 inline-flex items-center gap-1 text-xs text-gray-500 hover:text-primary-600" onClick={() => setSelectedNoteId(null)}><ArrowLeft className="h-3.5 w-3.5" />返回笔记列表</button>
        {selectedNote.isLoading && <Loader2 className="mx-auto my-8 h-5 w-5 animate-spin text-gray-400" />}
        {selectedNote.data && <InlineNoteEditor key={selectedNote.data.id} note={selectedNote.data} currentPage={currentPage} dock={props.dock} />}
        {selectedNote.isError && <p className="py-6 text-center text-xs text-red-500">笔记加载失败，请返回后重试。</p>}
      </> : <>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-gray-500">当前论文关联笔记</p>
        <button type="button" onClick={createPaperNote} disabled={createNote.isPending} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-primary-600 hover:bg-primary-50 disabled:cursor-wait disabled:opacity-60 dark:hover:bg-primary-950/30">
          {createNote.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FilePlus2 className="h-3.5 w-3.5" />}
          新建本页笔记
        </button>
      </div>
      {notes.data?.map((note) => <button type="button" key={note.id} onClick={() => setSelectedNoteId(note.id)} className="mb-1 block w-full rounded px-2 py-2 text-left text-xs hover:bg-gray-100 dark:hover:bg-slate-800"><span className="block truncate">{note.title}</span><span className="mt-0.5 block text-[10px] text-gray-400">在 Reader 中编辑</span></button>)}
      {!notes.isLoading && !notes.data?.length && <div className="rounded-lg border border-dashed border-gray-200 px-3 py-6 text-center dark:border-slate-700"><p className="text-xs text-gray-400">暂无关联笔记</p><p className="mt-1 text-[11px] text-gray-400">可直接新建，系统会自动关联当前论文</p></div>}
      {createNote.isError && <p className="mt-2 text-xs text-red-500">创建失败，请重试。</p>}
      </>}
    </div>}
    {activeTab === "ai" && <AIPanel paperId={props.paperId} pageNumber={currentPage} onOpenCitation={props.onOpenCitation} />}
    {activeTab === "translations" && <TranslationHistoryPanel history={props.translationHistory} onRetry={props.onRetryTranslation} />}
    {activeTab === "mindmap" && <ReaderMindMap paperId={props.paperId} />}
  </aside>;
}

function TranslationHistoryPanel({ history, onRetry }: { history: TranslationHistoryItem[]; onRetry: () => void }) {
  return <div className="min-h-0 flex-1 overflow-y-auto p-3">
    <div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-medium">翻译记录</h3><span className="text-[10px] text-gray-400">{history.length} 条</span></div>
    {!history.length && <p className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-xs text-gray-400 dark:border-slate-700">选中文本后点击翻译，结果会显示在这里。</p>}
    <div className="space-y-3">{history.map((item) => <article key={item.id} className="rounded-lg border border-gray-100 p-3 dark:border-slate-700"><p className="mb-2 text-[10px] text-gray-400">第 {item.pageNumber} 页 · {new Date(item.createdAt).toLocaleTimeString()}</p><p className="line-clamp-3 border-l-2 border-gray-200 pl-2 text-xs text-gray-500 dark:border-slate-600">{item.sourceText}</p>{item.pending && <div className="mt-2 flex items-center gap-1 text-xs text-gray-400"><Loader2 className="h-3.5 w-3.5 animate-spin"/>正在翻译…</div>}{item.error && <div className="mt-2 flex items-center justify-between gap-2 text-xs text-red-500"><span>{item.error}</span><button type="button" className="text-primary-600" onClick={onRetry}>重试</button></div>}{item.result && <div className="prose prose-sm mt-2 max-w-none text-xs dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{item.result.translated_text}</ReactMarkdown></div>}</article>)}</div>
  </div>;
}

function InlineNoteEditor({ note, currentPage, dock }: { note: Note; currentPage: number; dock: ReaderDock }) {
  const save = useSaveNote(note.id);
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content_markdown);
  const [saved, setSaved] = useState(false);
  const editorRef = useRef<HTMLDivElement>(null);
  const lastSavedRef = useRef({ title: note.title, content: note.content_markdown });
  const previewLayout = dock === "bottom" ? "horizontal" : "vertical";
  const persist = () => {
    const nextTitle = title.trim();
    if (!nextTitle || save.isPending || (nextTitle === lastSavedRef.current.title && content === lastSavedRef.current.content)) return;
    save.mutate({ paper_id: note.paper_id, title: nextTitle, content_markdown: content, note_type: note.note_type }, { onSuccess: () => { lastSavedRef.current = { title: nextTitle, content }; setSaved(true); } });
  };
  const insertPage = () => {
    setSaved(false);
    setContent((value) => `${value.replace(/\s*$/, "")}\n\n## 第 ${currentPage} 页\n\n`);
  };
  return <div ref={editorRef} className="space-y-2" onBlur={(event) => { if (!editorRef.current?.contains(event.relatedTarget as Node | null)) persist(); }}>
    <input className="input h-8 text-xs font-medium" value={title} maxLength={500} onChange={(event) => { setSaved(false); setTitle(event.target.value); }} aria-label="笔记标题" />
    <div className="flex items-center justify-between gap-2"><span className="text-[10px] text-gray-400">Markdown · 第 {currentPage} 页 · {dock === "bottom" ? "左右" : "上下"}实时预览</span><button type="button" className="text-[10px] text-primary-600 hover:underline" onClick={insertPage}>插入当前页</button></div>
    <div className={`grid min-h-[24rem] gap-2 ${previewLayout === "horizontal" ? "grid-cols-2" : "grid-rows-2"}`}>
      <textarea className="input h-full min-h-[12rem] resize-none font-mono text-xs leading-5" value={content} onChange={(event) => { setSaved(false); setContent(event.target.value); }} placeholder={`记录第 ${currentPage} 页的要点…`} aria-label="笔记内容" />
      <div className="prose prose-sm h-full min-h-[12rem] max-w-none overflow-y-auto rounded-lg border border-gray-200 p-3 text-xs dark:prose-invert dark:border-slate-700"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content || "*预览将在输入时实时显示*"}</ReactMarkdown></div>
    </div>
    <button type="button" className="btn-primary w-full justify-center text-xs" disabled={!title.trim() || save.isPending} onClick={persist}>{save.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}{save.isPending ? "保存中…" : "保存笔记"}</button>
    {saved && <p className="text-center text-[10px] text-emerald-600">已保存，无需离开 Reader。</p>}
    {save.isError && <p className="text-center text-[10px] text-red-500">保存失败，请重试。</p>}
  </div>;
}

function ReaderMindMap({ paperId }: { paperId: string }) {
  const map = useMindMap(paperId); const scopeKey = `paper:${paperId}`; const layout = useGraphLayout("mind_map", scopeKey); const save = useSaveGraphLayout(); const timer = useRef<number>();
  const createNode = useCreateMindMapNode(paperId); const updateNode = useUpdateMindMapNode(paperId); const deleteNode = useDeleteMindMapNode(paperId);
  const updateRoot = useMutation({ mutationFn: (title: string) => api.patch(`/papers/${paperId}`, { title }), onSuccess: () => void map.refetch() });
  const createEdge = useCreateMindMapEdge(paperId); const updateEdge = useUpdateMindMapEdge(paperId); const deleteEdge = useDeleteMindMapEdge(paperId);
  const [selectedId, setSelectedId] = useState<string>(); const [selectedEdgeId, setSelectedEdgeId] = useState<string>();
  const [editorOpen, setEditorOpen] = useState(false); const nodeTitleRef = useRef<HTMLInputElement>(null);
  const [nodeTitle, setNodeTitle] = useState(""); const [nodeSummary, setNodeSummary] = useState("");
  const [edgeSource, setEdgeSource] = useState(""); const [edgeTarget, setEdgeTarget] = useState(""); const [edgeRelation, setEdgeRelation] = useState("关联");
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const nodes: CanvasNode[] = (map.data?.nodes ?? []).map((node) => ({ id: node.id, title: node.title, subtitle: node.summary || (node.node_type === "manual" ? "" : node.node_type), kind: node.node_type, root: node.node_type === "paper" }));
  const edges: CanvasEdge[] = (map.data?.edges ?? []).map((edge, index) => ({ id: edge.id ?? `${edge.source}:${edge.target}:${index}`, source: edge.source, target: edge.target, label: edge.relation, kind: edge.relation === "supports" ? "supports" : "contains" }));
  const selectedNode = map.data?.nodes.find((node) => node.id === selectedId); const selectedEdge = map.data?.edges.find((edge) => edge.id === selectedEdgeId);
  const selectNode = (id: string) => { const node = map.data?.nodes.find((item) => item.id === id); setSelectedId(id); setSelectedEdgeId(undefined); if (node?.node_type === "manual") { setNodeTitle(node.title); setNodeSummary(node.summary ?? ""); } };
  const selectEdge = (id: string) => { const edge = map.data?.edges.find((item) => item.id === id); setSelectedEdgeId(id); setSelectedId(undefined); if (edge?.manual) setEdgeRelation(edge.relation); };
  const schedule = (positions: Record<string, Point>) => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => save.mutate({ graphType: "mind_map", scopeKey, positions }), 600); };
  if (map.isLoading || layout.isLoading) return <div className="flex flex-1 items-center justify-center text-xs text-gray-400"><Loader2 className="mr-2 h-4 w-4 animate-spin" />加载思维导图…</div>;
  const manualNodeId = selectedNode?.node_type === "manual" ? selectedNode.entity_id : undefined; const manualEdgeId = selectedEdge?.manual ? selectedEdge.id : undefined;
  const busy = createNode.isPending || updateNode.isPending || deleteNode.isPending || createEdge.isPending || updateEdge.isPending || deleteEdge.isPending;
  const createChild = async (parentId: string, title = "", summary = "") => {
    if (busy) return;
    const previousIds = new Set(map.data?.nodes.map((node) => node.id) ?? []);
    const result = await createNode.mutateAsync({ title, summary });
    const child = result.nodes.find((node) => node.node_type === "manual" && !previousIds.has(node.id));
    if (!child) return;
    const connected = await createEdge.mutateAsync({ source: parentId, target: child.id, relation: "关联" });
    const siblingIds = connected.edges.filter((edge) => edge.source === parentId).map((edge) => edge.target);
    const parentIndex = nodes.findIndex((node) => node.id === parentId);
    const parentPosition = layout.data?.positions[parentId] ?? { x: 40 + (Math.max(parentIndex, 0) % 3) * 230, y: 40 + Math.floor(Math.max(parentIndex, 0) / 3) * 125 };
    const positions = { ...(layout.data?.positions ?? {}) };
    siblingIds.forEach((id, index) => { positions[id] = { ...(positions[id] ?? {}), x: parentPosition.x + 230, y: parentPosition.y + (index - (siblingIds.length - 1) / 2) * 96 }; });
    save.mutate({ graphType: "mind_map", scopeKey, positions });
    selectNode(child.id);
  };
  const deleteSelection = () => {
    if (manualNodeId) {
      const parentId = map.data?.edges.find((edge) => edge.target === selectedId)?.source;
      deleteNode.mutate(manualNodeId, { onSuccess: (nextMap) => {
        setSelectedId(undefined);
        if (!parentId) return;
        const childIds = nextMap.edges.filter((edge) => edge.source === parentId).map((edge) => edge.target);
        const childY = childIds.map((id) => layout.data?.positions[id]?.y).filter((value): value is number => typeof value === "number");
        if (!childY.length) return;
        const positions = { ...(layout.data?.positions ?? {}) };
        const current = positions[parentId] ?? { x: 40, y: 40 };
        positions[parentId] = { ...current, y: (Math.min(...childY) + Math.max(...childY)) / 2 };
        save.mutate({ graphType: "mind_map", scopeKey, positions });
      } });
    }
    else if (manualEdgeId) deleteEdge.mutate(manualEdgeId, { onSuccess: () => setSelectedEdgeId(undefined) });
  };
  const connectNodes = (source: string, target: string) => createEdge.mutate({ source, target, relation: "关联" });
  return <div className="flex min-h-0 flex-1 flex-col gap-2 p-2">
    <details className="hidden" open={editorOpen || (!map.data?.has_profile && nodes.length <= 1)} onToggle={(event) => setEditorOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-200">手工编辑思维导图</summary>
      <div className="mt-2 space-y-2">
        <div className="grid grid-cols-[1fr_auto] gap-1"><input ref={nodeTitleRef} className="input h-8 text-xs" value={nodeTitle} onChange={(event) => setNodeTitle(event.target.value)} placeholder="节点名称" /><button type="button" className="btn-secondary px-2" disabled={!nodeTitle.trim() || busy} onClick={async () => { if (selectedId) await createChild(selectedId, nodeTitle.trim(), nodeSummary.trim()); else await createNode.mutateAsync({ title: nodeTitle.trim(), summary: nodeSummary.trim() }); setNodeTitle(""); setNodeSummary(""); }}><Plus className="h-3.5 w-3.5" />新增</button></div>
        <input className="input h-8 text-xs" value={nodeSummary} onChange={(event) => setNodeSummary(event.target.value)} placeholder="节点说明（可选）" />
        {manualNodeId && <div className="flex gap-1"><button type="button" className="btn-secondary flex-1 justify-center" disabled={!nodeTitle.trim() || busy} onClick={() => updateNode.mutate({ id: manualNodeId, title: nodeTitle.trim(), summary: nodeSummary.trim() })}><Save className="h-3.5 w-3.5" />更新选中节点</button><button type="button" className="btn-secondary px-2 text-red-600" disabled={busy} onClick={() => deleteNode.mutate(manualNodeId, { onSuccess: () => setSelectedId(undefined) })} title="删除选中节点及其手工关系"><Trash2 className="h-3.5 w-3.5" /></button></div>}
        <div className="grid grid-cols-2 gap-1"><select className="input h-8 text-xs" value={edgeSource} onChange={(event) => setEdgeSource(event.target.value)}><option value="">起点</option>{map.data?.nodes.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}</select><select className="input h-8 text-xs" value={edgeTarget} onChange={(event) => setEdgeTarget(event.target.value)}><option value="">终点</option>{map.data?.nodes.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}</select></div>
        <div className="grid grid-cols-[1fr_auto] gap-1"><input className="input h-8 text-xs" value={edgeRelation} onChange={(event) => setEdgeRelation(event.target.value)} placeholder="关系名称" /><button type="button" className="btn-secondary px-2" disabled={!edgeSource || !edgeTarget || edgeSource === edgeTarget || !edgeRelation.trim() || busy} onClick={() => createEdge.mutate({ source: edgeSource, target: edgeTarget, relation: edgeRelation.trim() })}><Plus className="h-3.5 w-3.5" />连线</button></div>
        {manualEdgeId && <div className="flex gap-1"><button type="button" className="btn-secondary flex-1 justify-center" disabled={!edgeRelation.trim() || busy} onClick={() => updateEdge.mutate({ id: manualEdgeId, relation: edgeRelation.trim() })}><Save className="h-3.5 w-3.5" />更新选中关系</button><button type="button" className="btn-secondary px-2 text-red-600" disabled={busy} onClick={() => deleteEdge.mutate(manualEdgeId, { onSuccess: () => setSelectedEdgeId(undefined) })}><Trash2 className="h-3.5 w-3.5" /></button></div>}
        {!map.data?.has_profile && <p className="text-[10px] leading-4 text-gray-400">当前没有结构化研究笔记；仍可完全手工创建节点和关系。</p>}
      </div>
    </details>
    <div className="min-h-0 flex-1"><MindMapFlowCanvas key={`${scopeKey}:${map.data?.profile_revision ?? 0}`} nodes={nodes} edges={edges} savedPositions={layout.data?.positions} selectedNodeId={selectedId} selectedEdgeId={selectedEdgeId} onNode={selectNode} onNodeUpdate={(id, title, summary) => { const node = map.data?.nodes.find((item) => item.id === id); if (node?.node_type === "manual" && node.entity_id) updateNode.mutate({ id: node.entity_id, title, summary }); else if (node?.node_type === "paper" && title) updateRoot.mutate(title); }} onEdge={selectEdge} onPositionsChange={schedule} onConnect={connectNodes} onCreateChild={(parentId) => void createChild(parentId)} onDeleteRequest={deleteSelection} /></div>
  </div>;
}

function Tab({ active, icon: Icon, label, title, onClick, onDragStart, onDrop }: { active: boolean; icon?: typeof Bot; label: string; title?: string; onClick: () => void; onDragStart: () => void; onDrop: () => void }) {
  return <button type="button" draggable onDragStart={onDragStart} onDragOver={(event) => event.preventDefault()} onDrop={onDrop} title={title ?? "拖动可调整标签顺序"} onClick={onClick} className={`reader-side-tab min-w-0 ${active ? "reader-side-tab-active" : ""}`}>{Icon && <Icon className="h-3.5 w-3.5" />}{label}</button>;
}
