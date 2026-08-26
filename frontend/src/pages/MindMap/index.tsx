import { useEffect, useRef, useState } from "react";
import { BrainCircuit, ExternalLink, Loader2 } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { GraphCanvas, type CanvasEdge, type CanvasNode } from "@/features/graph/GraphCanvas";
import { useGraphLayout, useMindMap, useSaveGraphLayout } from "@/features/graph/hooks";
import type { MindMapNode, Point } from "@/features/graph/types";
import { useNote } from "@/features/notes/hooks";
import { usePapers } from "@/features/paper/hooks";

export default function MindMapPage() {
  const navigate = useNavigate(); const [params, setParams] = useSearchParams(); const paperId = params.get("paper_id") || undefined;
  const papers = usePapers({ page_size: 100 }); const map = useMindMap(paperId); const scopeKey = paperId ? `paper:${paperId}` : "empty";
  const layout = useGraphLayout("mind_map", scopeKey); const save = useSaveGraphLayout(); const timer = useRef<number>(); const [selectedId, setSelectedId] = useState<string>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const selected = map.data?.nodes.find((node) => node.id === selectedId);
  const nodes: CanvasNode[] = (map.data?.nodes ?? []).map((node) => ({ id: node.id, title: node.title, subtitle: node.summary || node.node_type, kind: node.node_type, root: node.node_type === "paper" }));
  const edges: CanvasEdge[] = (map.data?.edges ?? []).map((edge, index) => ({ id: `${edge.source}:${edge.target}:${index}`, source: edge.source, target: edge.target, label: edge.relation === "supports" ? "supports" : undefined, kind: edge.relation === "supports" ? "supports" : "contains" }));
  const schedule = (positions: Record<string, Point>) => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => save.mutate({ graphType: "mind_map", scopeKey, positions }), 600); };
  return <div className="flex h-full min-h-0 flex-col bg-gray-50"><header className="flex items-center justify-between border-b bg-white px-6 py-4"><div><h1 className="flex items-center gap-2 text-lg font-semibold"><BrainCircuit className="h-5 w-5 text-primary-600" />论文思维导图</h1><p className="mt-1 text-xs text-gray-500">由结构化 Research Note 动态派生，不保存第二份研究内容</p></div><select className="input w-80" value={paperId ?? ""} onChange={(e) => { const next = new URLSearchParams(); if (e.target.value) next.set("paper_id", e.target.value); setParams(next); setSelectedId(undefined); }}><option value="">选择论文…</option>{papers.data?.items.map((paper) => <option key={paper.id} value={paper.id}>{paper.title}</option>)}</select></header>
    {!paperId ? <div className="flex flex-1 items-center justify-center text-sm text-gray-400">选择一篇论文查看其研究逻辑</div> : map.isLoading || layout.isLoading ? <div className="flex flex-1 items-center justify-center text-sm text-gray-500"><Loader2 className="mr-2 h-4 w-4 animate-spin" />生成思维导图…</div> : map.data && <div className="flex min-h-0 flex-1"><main className="min-w-0 flex-1 p-4">{!map.data.has_profile && <div className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">建立结构化研究笔记后，可生成完整思维导图。</div>}<GraphCanvas key={`${scopeKey}:${map.data.profile_revision ?? 0}:${layout.data?.updated_at ?? "auto"}`} nodes={nodes} edges={edges} rootId={`paper:${paperId}`} savedPositions={layout.data?.positions} selectedNodeId={selectedId} onNode={setSelectedId} onEdge={() => undefined} onPositionsChange={schedule} /></main><aside className="w-80 overflow-y-auto border-l bg-white p-5">{selected ? <MindMapInspector node={selected} noteId={map.data.note_id} onReader={(paper, page) => navigate(`/reader/${paper}?page=${page}`)} onNote={() => map.data?.note_id && navigate(`/notes/${map.data.note_id}`)} /> : <p className="py-10 text-center text-sm text-gray-400">选择节点查看结构化内容与证据</p>}</aside></div>}
  </div>;
}

function MindMapInspector({ node, noteId, onReader, onNote }: { node: MindMapNode; noteId?: string | null; onReader: (paperId: string, page: number) => void; onNote: () => void }) {
  const note = useNote(noteId ?? undefined); const evidence = (note.data?.evidence ?? []).filter((item) => node.evidence_ids.includes(item.id));
  return <div><span className="text-xs font-medium uppercase text-primary-600">{node.node_type.replace("_", " ")}</span><h2 className="mt-2 font-semibold">{node.title}</h2>{node.summary && <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-600">{node.summary}</p>}<div className="mt-5 space-y-2">{evidence.map((item) => <button key={item.id} className="w-full rounded-lg border p-3 text-left text-xs hover:bg-gray-50" onClick={() => onReader(item.annotation.paper_id, item.annotation.page_number)}><b>Evidence · Page {item.annotation.page_number}</b><p className="mt-1 line-clamp-3 text-gray-500">{item.quote_snapshot || item.annotation.selected_text || item.annotation.comment}</p></button>)}</div>{noteId && <button className="btn-primary mt-5 w-full justify-center" onClick={onNote}><ExternalLink className="h-4 w-4" />打开结构化笔记</button>}</div>;
}
