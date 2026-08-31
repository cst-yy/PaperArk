import {
  Background,
  Controls,
  Handle,
  MarkerType,
  NodeResizer,
  Position,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "@xyflow/react/dist/style.css";

import type { CanvasEdge, CanvasNode } from "./GraphCanvas";
import type { Point } from "./types";

type MindMapNodeData = { title: string; subtitle?: string; root?: boolean; editable?: boolean; background: string; textColor: string; fontSize: number; onResizeEnd: (id: string, width: number, height: number) => void; onStyle: (id: string, style: Partial<Point>) => void; onUpdate: (id: string, title: string, summary: string) => void };
type MindMapFlowNode = Node<MindMapNodeData, "mindMap">;
type FlowDragEvent = globalThis.MouseEvent | globalThis.TouchEvent;

function autoNodeSize(title: string, subtitle: string | undefined, fontSize: number): { width: number; height: number } {
  const longestLine = Math.max(Array.from(title || " ").length, Array.from(subtitle || "").length);
  const width = Math.min(560, Math.max(176, 176 + Math.max(0, Math.min(48, longestLine - 22)) * 5));
  const charsPerLine = Math.max(12, Math.floor((width - 24) / (fontSize * 0.95)));
  const titleLines = Math.max(1, Math.ceil(Array.from(title || " ").length / charsPerLine));
  const subtitleLines = subtitle ? Math.max(1, Math.ceil(Array.from(subtitle).length / charsPerLine)) : 0;
  const titleLineHeight = Math.max(16, fontSize * 1.45);
  const subtitleLineHeight = Math.max(14, (fontSize - 2) * 1.35);
  const height = Math.min(320, Math.max(72, Math.ceil(20 + titleLines * titleLineHeight + (subtitleLines ? subtitleLines * subtitleLineHeight + 4 : 0) + 20)));
  return { width, height };
}

function descendantsOf(rootId: string, edges: CanvasEdge[]): Set<string> {
  const children = new Map<string, string[]>();
  for (const edge of edges) children.set(edge.source, [...(children.get(edge.source) ?? []), edge.target]);
  const result = new Set<string>();
  const queue = [...(children.get(rootId) ?? [])];
  while (queue.length) {
    const id = queue.shift();
    if (!id || result.has(id)) continue;
    result.add(id);
    queue.push(...(children.get(id) ?? []));
  }
  return result;
}

interface Props {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  savedPositions?: Record<string, Point>;
  selectedNodeId?: string;
  selectedEdgeId?: string;
  onNode: (id: string) => void;
  onNodeUpdate: (id: string, title: string, summary: string) => void;
  onEdge: (id: string) => void;
  onConnect: (source: string, target: string) => void;
  onCreateChild: (parentId: string) => void;
  onDeleteRequest: () => void;
  onPositionsChange: (positions: Record<string, Point>) => void;
}

function MindMapNode({ id, data, selected }: NodeProps<MindMapFlowNode>) {
  const [editing, setEditing] = useState(Boolean(data.editable && !data.title));
  const [title, setTitle] = useState(data.title);
  const [summary, setSummary] = useState(data.subtitle ?? "");
  const commit = () => {
    const nextTitle = title.trim();
    if (data.editable && (nextTitle !== data.title || summary.trim() !== (data.subtitle ?? ""))) data.onUpdate(id, nextTitle, summary.trim());
    else { setTitle(data.title); setSummary(data.subtitle ?? ""); }
    setEditing(false);
  };
  return <div className={`relative flex h-full w-full min-w-36 items-center justify-center rounded-xl border px-3 py-2 text-center shadow-sm transition ${selected ? "border-primary-500 ring-2 ring-primary-200" : data.root ? "border-primary-300" : "border-gray-200"}`} style={{ backgroundColor: data.background, color: data.textColor }}>
    {selected && <div className="nodrag nowheel absolute -top-9 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-md border bg-white px-1.5 py-1 shadow-md" onPointerDown={(event) => event.stopPropagation()}>
      <input type="color" value={data.background} title="节点背景色" onChange={(event) => data.onStyle(id, { background: event.target.value })} className="h-5 w-5 cursor-pointer border-0 bg-transparent p-0" />
      <input type="color" value={data.textColor} title="文字颜色" onChange={(event) => data.onStyle(id, { text_color: event.target.value })} className="h-5 w-5 cursor-pointer border-0 bg-transparent p-0" />
      <input type="range" min="10" max="28" step="1" value={data.fontSize} title="字体大小" onChange={(event) => data.onStyle(id, { font_size: Number(event.target.value) })} className="w-16" />
    </div>}
    <NodeResizer isVisible={selected} minWidth={144} minHeight={56} maxWidth={640} maxHeight={420} lineClassName="!border-primary-400" handleClassName="!h-2.5 !w-2.5 !border-primary-500 !bg-white" onResizeEnd={(_, size) => data.onResizeEnd(id, size.width, size.height)} />
    <Handle type="target" position={Position.Left} className="!h-3 !w-3 !border-2 !border-white !bg-primary-500" />
    {editing ? <div className="nodrag nowheel flex w-full flex-col items-center justify-center" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as globalThis.Node | null)) commit(); }} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); commit(); } else if (event.key === "Escape") { setTitle(data.title); setSummary(data.subtitle ?? ""); setEditing(false); } }}>
      <input autoFocus className="w-full border-0 bg-transparent text-center font-semibold outline-none" style={{ fontSize: data.fontSize, color: data.textColor }} value={title} onChange={(event) => setTitle(event.target.value)} aria-label="节点名称" />
      <textarea className="mt-1 h-10 w-full resize-none border-0 bg-transparent text-center leading-4 opacity-75 outline-none" style={{ fontSize: Math.max(9, data.fontSize - 2), color: data.textColor }} value={summary} onChange={(event) => setSummary(event.target.value)} aria-label="节点说明" />
    </div> : <div className="flex h-full w-full flex-col items-center justify-center" onDoubleClick={(event) => { if (!data.editable) return; event.stopPropagation(); setEditing(true); }}>
      <p className="w-full whitespace-normal break-words text-center font-semibold leading-5" style={{ fontSize: data.fontSize, color: data.textColor, overflowWrap: "anywhere" }}>{data.title || "\u00a0"}</p>
      {data.subtitle && <p className="mt-0.5 w-full whitespace-normal break-words text-center leading-4 opacity-75" style={{ fontSize: Math.max(9, data.fontSize - 2), color: data.textColor, overflowWrap: "anywhere" }}>{data.subtitle}</p>}
    </div>}
    <Handle type="source" position={Position.Right} className={`!border-2 !border-white !bg-primary-500 ${selected ? "!h-4 !w-4" : "!h-3 !w-3"}`} />
  </div>;
}

const nodeTypes = { mindMap: MindMapNode };

export function MindMapFlowCanvas(props: Props) {
  const onPositionsChange = props.onPositionsChange;
  const setNodesRef = useRef<((updater: (current: MindMapFlowNode[]) => MindMapFlowNode[]) => void) | null>(null);
  const savedPositionsRef = useRef<Record<string, Point>>(props.savedPositions ?? {});
  useEffect(() => { savedPositionsRef.current = props.savedPositions ?? {}; }, [props.savedPositions]);
  const emitPositionPatch = useCallback((id: string, patch: Partial<Point>) => {
    const next = { ...savedPositionsRef.current, [id]: { ...(savedPositionsRef.current[id] ?? { x: 0, y: 0 }), ...patch } };
    savedPositionsRef.current = next;
    onPositionsChange(next);
  }, [onPositionsChange]);
  const resizeNode = useCallback((id: string, width: number, height: number) => {
    setNodesRef.current?.((current) => current.map((node) => node.id === id ? { ...node, width, height, style: { ...node.style, width, height } } : node));
    emitPositionPatch(id, { width, height });
  }, [emitPositionPatch]);
  const styleNode = useCallback((id: string, style: Partial<Point>) => {
    setNodesRef.current?.((current) => current.map((node) => node.id === id ? { ...node, data: {
      ...node.data,
      background: style.background ?? node.data.background,
      textColor: style.text_color ?? node.data.textColor,
      fontSize: style.font_size ?? node.data.fontSize,
    }, style: (() => { const fontSize = style.font_size ?? node.data.fontSize; const auto = autoNodeSize(node.data.title, node.data.subtitle, fontSize); const currentWidth = Number(node.style?.width ?? node.width ?? auto.width); const currentHeight = Number(node.style?.height ?? node.height ?? auto.height); return { ...node.style, width: Math.max(currentWidth, auto.width), height: Math.max(currentHeight, auto.height) }; })() } : node));
    emitPositionPatch(id, style);
  }, [emitPositionPatch]);
  const initialNodes = useMemo<MindMapFlowNode[]>(() => props.nodes.map((node, index) => ({
    id: node.id,
    type: "mindMap",
    position: props.savedPositions?.[node.id] ?? { x: 40 + (index % 3) * 230, y: 40 + Math.floor(index / 3) * 125 },
    style: (() => { const saved = props.savedPositions?.[node.id]; const auto = autoNodeSize(node.title, node.subtitle, saved?.font_size ?? 14); return { width: saved?.width ?? auto.width, height: saved?.height ?? auto.height }; })(),
    data: { title: node.title, subtitle: node.subtitle, root: node.root, editable: node.kind === "manual" || node.root, background: props.savedPositions?.[node.id]?.background ?? (node.root ? "#eef2ff" : "#ffffff"), textColor: props.savedPositions?.[node.id]?.text_color ?? "#111827", fontSize: props.savedPositions?.[node.id]?.font_size ?? 14, onResizeEnd: resizeNode, onStyle: styleNode, onUpdate: props.onNodeUpdate },
    selected: node.id === props.selectedNodeId,
  })), [props.nodes, props.savedPositions, props.selectedNodeId, props.onNodeUpdate, resizeNode, styleNode]);
  const initialEdges = useMemo<Edge[]>(() => props.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    selected: edge.id === props.selectedEdgeId,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { strokeWidth: 1.6 },
  })), [props.edges, props.selectedEdgeId]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  useEffect(() => { setNodesRef.current = setNodes; return () => { setNodesRef.current = null; }; }, [setNodes]);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const flowRef = useRef<ReactFlowInstance<MindMapFlowNode, Edge> | null>(null);
  const dragGroupRef = useRef<{ rootId: string; initial: Record<string, Point> } | null>(null);
  const nodeCountRef = useRef(initialNodes.length);
  useEffect(() => setNodes(initialNodes), [initialNodes, setNodes]);
  useEffect(() => setEdges(initialEdges), [initialEdges, setEdges]);
  useEffect(() => {
    if (initialNodes.length === nodeCountRef.current) return;
    nodeCountRef.current = initialNodes.length;
    window.requestAnimationFrame(() => void flowRef.current?.fitView({ padding: 0.08, minZoom: 0.45, maxZoom: 1, duration: 220 }));
  }, [initialNodes.length]);

  const persistPositions = useCallback(() => {
    const next = Object.fromEntries(nodes.map((node) => [node.id, {
      ...node.position,
      width: typeof node.style?.width === "number" ? node.style.width : node.measured?.width ?? node.width,
      height: typeof node.style?.height === "number" ? node.style.height : node.measured?.height ?? node.height,
      background: node.data.background,
      text_color: node.data.textColor,
      font_size: node.data.fontSize,
    }])) as Record<string, Point>;
    savedPositionsRef.current = next;
    onPositionsChange(next);
  }, [nodes, onPositionsChange]);
  const startGroupDrag = useCallback((_event: FlowDragEvent, node: MindMapFlowNode) => {
    const ids = new Set([node.id, ...descendantsOf(node.id, props.edges)]);
    const initial: Record<string, Point> = {};
    for (const item of nodes) if (ids.has(item.id)) initial[item.id] = { x: item.position.x, y: item.position.y };
    dragGroupRef.current = { rootId: node.id, initial };
  }, [nodes, props.edges]);
  const moveGroupDrag = useCallback((_event: FlowDragEvent, node: MindMapFlowNode) => {
    const group = dragGroupRef.current;
    const initialRoot = group?.initial[node.id];
    if (!group || group.rootId !== node.id || !initialRoot) return;
    const delta = { x: node.position.x - initialRoot.x, y: node.position.y - initialRoot.y };
    setNodes((current) => current.map((item) => {
      const start = group.initial[item.id];
      return start && item.id !== node.id ? { ...item, position: { x: start.x + delta.x, y: start.y + delta.y } } : item;
    }));
  }, [setNodes]);
  const stopGroupDrag = useCallback(() => {
    dragGroupRef.current = null;
    window.requestAnimationFrame(() => persistPositions());
  }, [persistPositions]);
  const connect = useCallback((connection: Connection) => {
    if (connection.source && connection.target && connection.source !== connection.target) props.onConnect(connection.source, connection.target);
  }, [props]);

  return <div
    ref={wrapperRef}
    className="h-full min-h-56 w-full overflow-hidden rounded-lg border border-gray-200 bg-slate-50 outline-none focus:ring-2 focus:ring-primary-200 dark:border-slate-700 dark:bg-slate-950"
    tabIndex={0}
    onKeyDown={(event) => {
      if (event.key === "Tab" && props.selectedNodeId) {
        event.preventDefault();
        props.onCreateChild(props.selectedNodeId);
      } else if ((event.key === "Backspace" || event.key === "Delete") && (props.selectedNodeId || props.selectedEdgeId)) {
        event.preventDefault();
        props.onDeleteRequest();
      }
    }}
  >
    <ReactFlow
      onInit={(instance) => { flowRef.current = instance; }}
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, node) => { props.onNode(node.id); wrapperRef.current?.focus(); }}
      onEdgeClick={(_, edge) => props.onEdge(edge.id)}
      onNodeDragStart={startGroupDrag}
      onNodeDrag={moveGroupDrag}
      onNodeDragStop={stopGroupDrag}
      onConnect={connect}
      fitView
      fitViewOptions={{ padding: 0.08, minZoom: 0.45, maxZoom: 1 }}
      minZoom={0.25}
      maxZoom={2}
      defaultEdgeOptions={{ type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed }, style: { strokeWidth: 1.6 } }}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={18} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  </div>;
}
