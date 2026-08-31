import { LocateFixed, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { Annotation, AnnotationColor, AnnotationLineStyle, UpdateAnnotationInput } from "@/features/annotation/types";

const palette = {
  yellow: { highlight: "rgba(250,204,21,.38)", line: "#ca8a04", area: "rgba(250,204,21,.18)" }, green: { highlight: "rgba(74,222,128,.34)", line: "#16a34a", area: "rgba(74,222,128,.16)" },
  blue: { highlight: "rgba(96,165,250,.34)", line: "#2563eb", area: "rgba(96,165,250,.16)" }, red: { highlight: "rgba(248,113,113,.34)", line: "#dc2626", area: "rgba(248,113,113,.16)" },
  purple: { highlight: "rgba(192,132,252,.34)", line: "#9333ea", area: "rgba(192,132,252,.16)" },
} as const;
const colors = Object.keys(palette) as AnnotationColor[];

export function AnnotationOverlayLayer({ pageNumber, annotations, activeAnnotationId, onUpdate, onDelete, onCommentOpen }: { pageNumber: number; annotations: Annotation[]; activeAnnotationId?: string | null; onUpdate: (id: string, input: UpdateAnnotationInput) => void; onDelete: (id: string) => void; onCommentOpen: (annotation: Annotation) => void }) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [hoveredCommentId, setHoveredCommentId] = useState<string | null>(null);
  const hideTimer = useRef<number>();
  const menuRef = useRef<HTMLDivElement>(null);
  const visible = annotations.filter((annotation) => annotation.page_number === pageNumber && annotation.position_data);
  const editing = visible.find((item) => item.id === editingId);
  const hoveredComment = visible.find((item) => item.id === hoveredCommentId && item.comment);
  const anchor = editing?.position_data ? (editing.position_data.kind === "area" ? editing.position_data.rect : editing.position_data.rects[0]) : null;
  const commentAnchor = hoveredComment?.position_data ? (hoveredComment.position_data.kind === "area" ? hoveredComment.position_data.rect : hoveredComment.position_data.rects[0]) : null;
  const showComment = (id: string) => { window.clearTimeout(hideTimer.current); setHoveredCommentId(id); };
  const hideComment = () => { window.clearTimeout(hideTimer.current); hideTimer.current = window.setTimeout(() => setHoveredCommentId(null), 120); };
  useEffect(() => {
    if (!editingId) return;
    const closeOutside = (event: PointerEvent) => {
      if (menuRef.current?.contains(event.target as Node)) return;
      const next = commentDraft.trim();
      if (editing && editing.type !== "area" && next !== (editing.comment ?? "")) onUpdate(editing.id, { comment: next || null });
      setEditingId(null);
    };
    document.addEventListener("pointerdown", closeOutside, true);
    return () => document.removeEventListener("pointerdown", closeOutside, true);
  }, [commentDraft, editing, editingId, onUpdate]);
  return <div className="pointer-events-none absolute inset-0 z-20" aria-label={`第 ${pageNumber} 页标注`}>
    {visible.flatMap((annotation) => {
      const position = annotation.position_data!; const rects = position.kind === "area" ? [position.rect] : position.rects;
      return rects.map((rect, index) => {
        const tone = palette[annotation.color ?? "yellow"]; const isArea = annotation.type === "area"; const isUnderline = annotation.type === "underline";
        return <button key={`${annotation.id}-${index}`} type="button" className={`absolute pointer-events-auto rounded-sm transition-shadow ${activeAnnotationId === annotation.id || editingId === annotation.id ? "ring-2 ring-primary-500 ring-offset-1" : ""}`} style={{ left: `${rect.x * 100}%`, top: `${rect.y * 100}%`, width: `${rect.width * 100}%`, height: `${(rect.height + (isUnderline ? 0.005 : 0)) * 100}%`, backgroundColor: isArea ? tone.area : isUnderline ? "transparent" : tone.highlight, border: isArea ? `2px solid ${tone.line}` : undefined, backgroundImage: isUnderline ? linePattern(annotation.line_style ?? "solid", tone.line) : undefined, backgroundPosition: isUnderline ? "left bottom" : undefined, backgroundRepeat: isUnderline ? "repeat-x" : undefined }} onMouseEnter={() => annotation.comment && showComment(annotation.id)} onMouseLeave={() => annotation.comment && hideComment()} onClick={(event) => { event.stopPropagation(); if (annotation.type === "comment" && annotation.comment) showComment(annotation.id); else { setEditingId(annotation.id); setCommentDraft(annotation.comment ?? ""); } }} aria-label={annotation.comment ? `评论：${annotation.comment}` : annotation.selected_text ?? "区域标注"} />;
      });
    })}
    {hoveredComment && commentAnchor && <button type="button" className="pointer-events-auto absolute z-40 w-64 rounded-lg border border-gray-200 bg-white p-2 text-left shadow-xl dark:border-slate-700 dark:bg-slate-900" style={{ left: `${Math.min(commentAnchor.x * 100, 70)}%`, top: `${Math.min((commentAnchor.y + commentAnchor.height) * 100 + 1, 84)}%` }} onMouseEnter={() => showComment(hoveredComment.id)} onMouseLeave={hideComment} onClick={(event) => { event.stopPropagation(); setHoveredCommentId(null); onCommentOpen(hoveredComment); }}>
      <span className="block truncate text-xs leading-5 text-gray-700 dark:text-gray-200">{hoveredComment.comment || "暂无评论内容，可在右侧补充"}</span>
      <span className="mt-1 block text-[10px] text-primary-600">点击在右侧批注中查看</span>
    </button>}
    {editing && anchor && <div ref={menuRef} className="pointer-events-auto absolute z-30 w-60 rounded-lg border border-gray-200 bg-white p-2 shadow-xl dark:border-slate-700 dark:bg-slate-900" style={{ left: `${Math.min(anchor.x * 100, 70)}%`, top: `${Math.min((anchor.y + anchor.height) * 100 + 1, 82)}%` }}>
      <div className="flex items-center justify-between"><span className="text-[11px] font-medium">修改{editing.type === "underline" ? "下划线" : editing.type === "comment" ? "评论" : "高亮"}</span><button type="button" aria-label="关闭批注菜单" onClick={() => { const next = commentDraft.trim(); if (editing.type !== "area" && next !== (editing.comment ?? "")) onUpdate(editing.id, { comment: next || null }); setEditingId(null); }}><X className="h-3.5 w-3.5" /></button></div>
      <div className="mt-2 flex gap-1">{colors.map((color) => <button key={color} type="button" aria-label={`改为${color}`} className={`h-5 w-5 rounded-full ${editing.color === color ? "ring-2 ring-primary-500 ring-offset-1" : ""}`} style={{ backgroundColor: palette[color].line }} onClick={() => onUpdate(editing.id, { color })} />)}</div>
      {editing.type === "underline" && <select className="mt-2 h-8 w-full rounded border border-gray-200 bg-white px-2 py-0 text-xs leading-8 dark:border-slate-700 dark:bg-slate-800" aria-label="修改下划线形状" value={editing.line_style ?? "solid"} onChange={(event) => onUpdate(editing.id, { line_style: event.target.value as AnnotationLineStyle })}><option value="solid">实线</option><option value="dashed">虚线</option><option value="dotted">点线</option><option value="double">双线</option><option value="wavy">波浪线</option></select>}
      {editing.type !== "area" && <textarea className="input mt-2 min-h-16 resize-y text-xs" value={commentDraft} maxLength={5000} placeholder="添加评论…" onChange={(event) => setCommentDraft(event.target.value)} onBlur={() => { const next = commentDraft.trim(); if (next !== (editing.comment ?? "")) onUpdate(editing.id, { comment: next || null }); }} />}
      <div className="mt-2 flex items-center justify-between"><button type="button" className="inline-flex items-center gap-1 text-xs text-primary-600" onClick={() => { setEditingId(null); onCommentOpen(editing); }}><LocateFixed className="h-3.5 w-3.5" />在批注中查看</button><button type="button" className="inline-flex items-center gap-1 text-xs text-red-500" onClick={() => { onDelete(editing.id); setEditingId(null); }}><Trash2 className="h-3.5 w-3.5" />删除</button></div>
    </div>}
  </div>;
}

function linePattern(style: AnnotationLineStyle, color: string) {
  const encoded = color.replace("#", "%23");
  const content = style === "wavy"
    ? `<path d='M0 3 Q2 0 4 3 T8 3' fill='none' stroke='${encoded}' stroke-width='1.5'/>`
    : style === "dashed"
      ? `<path d='M0 3 H6' stroke='${encoded}' stroke-width='2'/>`
      : style === "dotted"
        ? `<circle cx='2' cy='3' r='1.2' fill='${encoded}'/>`
        : style === "double"
          ? `<path d='M0 1.5 H8 M0 4 H8' stroke='${encoded}' stroke-width='1'/>`
          : `<path d='M0 3 H8' stroke='${encoded}' stroke-width='2'/>`;
  const width = style === "dashed" ? 10 : style === "dotted" ? 6 : 8;
  return `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='${width}' height='5' viewBox='0 0 ${width} 5'%3E${content}%3C/svg%3E")`;
}
