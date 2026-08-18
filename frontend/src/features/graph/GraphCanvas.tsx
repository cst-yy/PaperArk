import { useState } from "react";
import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";

import type { Point } from "./types";

export interface CanvasNode { id: string; title: string; subtitle?: string; kind?: string; root?: boolean }
export interface CanvasEdge { id: string; source: string; target: string; label?: string; origin?: string; undirected?: boolean; kind?: string }

const EDGE_COLORS: Record<string, string> = { cites: "#64748b", extends: "#4f46e5", improves: "#059669", contrasts: "#dc2626", supports: "#0891b2", uses: "#d97706", similar: "#9333ea", contains: "#94a3b8" };

function deterministicLayout(nodes: CanvasNode[], edges: CanvasEdge[], rootId?: string): Record<string, Point> {
  const result: Record<string, Point> = {};
  const root = rootId && nodes.some((node) => node.id === rootId) ? rootId : nodes[0]?.id;
  if (!root) return result;
  result[root] = { x: 520, y: 330 };
  const distance = new Map<string, number>([[root, 0]]); let frontier = [root];
  for (let depth = 1; frontier.length && depth < 5; depth++) {
    const next: string[] = [];
    for (const id of frontier) for (const edge of edges) {
      const other = edge.source === id ? edge.target : edge.target === id ? edge.source : undefined;
      if (other && !distance.has(other)) { distance.set(other, depth); next.push(other); }
    }
    frontier = next;
  }
  const groups = new Map<number, CanvasNode[]>();
  for (const node of nodes.filter((item) => item.id !== root)) {
    const level = distance.get(node.id) ?? 3;
    groups.set(level, [...(groups.get(level) ?? []), node]);
  }
  for (const [level, values] of [...groups].sort(([a], [b]) => a - b)) values
    .sort((a, b) => a.id.localeCompare(b.id)).forEach((node, index) => {
      const angle = (Math.PI * 2 * index / values.length) - Math.PI / 2 + level * .22;
      const radius = 180 + level * 125;
      result[node.id] = { x: 520 + Math.cos(angle) * radius, y: 330 + Math.sin(angle) * radius };
    });
  return result;
}

export function GraphCanvas({ nodes, edges, rootId, savedPositions, selectedNodeId, selectedEdgeId,
  onNode, onEdge, onPositionsChange }: { nodes: CanvasNode[]; edges: CanvasEdge[]; rootId?: string;
  savedPositions?: Record<string, Point>; selectedNodeId?: string; selectedEdgeId?: string;
  onNode: (id: string) => void; onEdge: (id: string) => void;
  onPositionsChange?: (positions: Record<string, Point>) => void }) {
  const automatic = deterministicLayout(nodes, edges, rootId);
  const [positions, setPositions] = useState<Record<string, Point>>(() => ({ ...automatic, ...savedPositions }));
  const [scale, setScale] = useState(1); const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [dragNode, setDragNode] = useState<string>(); const [panStart, setPanStart] = useState<Point>();
  const moveNode = (id: string, point: Point) => { const next = { ...positions, [id]: point }; setPositions(next); onPositionsChange?.(next); };
  const reset = () => { setPositions(automatic); onPositionsChange?.(automatic); };
  if (!nodes.length) return <div className="flex h-full min-h-[560px] items-center justify-center rounded-xl border border-dashed bg-white text-sm text-gray-400">当前范围暂无关系数据</div>;
  return <div className="relative h-full min-h-[560px] overflow-hidden rounded-xl border bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
    <div className="absolute right-3 top-3 z-10 flex rounded-lg border bg-white shadow dark:border-slate-700 dark:bg-slate-800">
      <button className="p-2" title="恢复自动布局" onClick={reset}><RotateCcw className="h-4 w-4" /></button>
      <button className="border-l p-2 dark:border-slate-700" title="缩小" onClick={() => setScale((v) => Math.max(.4, v - .15))}><ZoomOut className="h-4 w-4" /></button>
      <button className="border-l p-2 dark:border-slate-700" title="放大" onClick={() => setScale((v) => Math.min(2.3, v + .15))}><ZoomIn className="h-4 w-4" /></button>
    </div>
    <svg className="h-full w-full touch-none" viewBox="0 0 1040 660"
      onWheel={(event) => { event.preventDefault(); setScale((v) => Math.min(2.3, Math.max(.4, v + (event.deltaY < 0 ? .1 : -.1)))); }}
      onPointerDown={(event) => { if (event.target === event.currentTarget) setPanStart({ x: event.clientX - pan.x, y: event.clientY - pan.y }); }}
      onPointerMove={(event) => { if (dragNode) moveNode(dragNode, { x: (event.nativeEvent.offsetX - pan.x) / scale, y: (event.nativeEvent.offsetY - pan.y) / scale }); else if (panStart) setPan({ x: event.clientX - panStart.x, y: event.clientY - panStart.y }); }}
      onPointerUp={() => { setDragNode(undefined); setPanStart(undefined); }} onPointerLeave={() => { setDragNode(undefined); setPanStart(undefined); }}>
      <defs><marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#64748b" /></marker></defs>
      <g transform={`translate(${pan.x} ${pan.y}) scale(${scale})`}>
        {edges.map((edge) => { const a = positions[edge.source], b = positions[edge.target]; if (!a || !b) return null;
          const color = EDGE_COLORS[edge.kind ?? ""] ?? "#64748b"; const selected = selectedEdgeId === edge.id;
          return <g key={edge.id} className="cursor-pointer" onPointerDown={(e) => { e.stopPropagation(); onEdge(edge.id); }}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth="14" />
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={color} strokeWidth={selected ? 3.5 : 2}
              strokeDasharray={edge.origin === "ai" ? "7 5" : edge.origin === "reference" ? "3 3" : undefined}
              markerEnd={edge.undirected ? undefined : "url(#graph-arrow)"} />
            {edge.label && <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 7} textAnchor="middle" fontSize="10" fill={color} className="select-none">{edge.label}</text>}
          </g>; })}
        {nodes.map((node) => { const p = positions[node.id]; if (!p) return null; const selected = selectedNodeId === node.id;
          return <g key={node.id} transform={`translate(${p.x - 78} ${p.y - 34})`} className="cursor-grab active:cursor-grabbing"
            onPointerDown={(e) => { e.stopPropagation(); setDragNode(node.id); onNode(node.id); }}>
            <rect width="156" height="68" rx="12" fill={node.root ? "#eef2ff" : node.kind === "experiment" ? "#ecfeff" : node.kind === "contribution" ? "#f0fdf4" : "#fff"} stroke={selected ? "#4f46e5" : node.root ? "#818cf8" : "#cbd5e1"} strokeWidth={selected ? 3 : 1.5} />
            <text x="12" y="25" fontSize="11" fontWeight="600" fill="#1e293b">{node.title.length > 24 ? `${node.title.slice(0, 24)}…` : node.title}</text>
            <text x="12" y="48" fontSize="10" fill="#64748b">{node.subtitle?.slice(0, 28) ?? node.kind ?? "Paper"}</text>
          </g>; })}
      </g>
    </svg>
  </div>;
}
