import { Highlighter, Languages, MessageSquare, PenLine } from "lucide-react";
import { useState } from "react";

import type { AnnotationColor, AnnotationLineStyle, SelectionContext } from "@/features/annotation/types";

const COLORS: Array<{ value: AnnotationColor; css: string; label: string }> = [
  { value: "yellow", css: "#facc15", label: "黄色" }, { value: "green", css: "#4ade80", label: "绿色" },
  { value: "blue", css: "#60a5fa", label: "蓝色" }, { value: "red", css: "#f87171", label: "红色" },
  { value: "purple", css: "#c084fc", label: "紫色" },
];

interface Props {
  selection: SelectionContext;
  onCreate: (type: "highlight" | "underline" | "comment", color: AnnotationColor, lineStyle?: AnnotationLineStyle, comment?: string) => void;
  onTranslate: () => void;
}

export function SelectionToolbar({ selection, onCreate, onTranslate }: Props) {
  const [mode, setMode] = useState<"highlight" | "underline" | null>(null);
  const [lineStyle, setLineStyle] = useState<AnnotationLineStyle>("solid");
  const [commenting, setCommenting] = useState(false);
  const [comment, setComment] = useState("");
  const center = selection.toolbarRect.left + selection.toolbarRect.width / 2;
  const left = Math.min(window.innerWidth - 160, Math.max(160, center));
  return <div className={`fixed z-50 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-900 ${commenting ? "" : "-translate-y-full"}`} style={{ left, top: commenting ? selection.toolbarRect.bottom + 8 : Math.max(12, selection.toolbarRect.top - 8) }} onMouseDown={(event) => event.preventDefault()}>
    <div className="flex items-center gap-1">
      <Tool label="高亮" icon={Highlighter} active={mode === "highlight"} onClick={() => setMode((value) => value === "highlight" ? null : "highlight")} />
      <Tool label="下划线" icon={PenLine} active={mode === "underline"} onClick={() => setMode((value) => value === "underline" ? null : "underline")} />
      <Tool label="评论" icon={MessageSquare} active={commenting} onClick={() => { setMode(null); setCommenting((value) => !value); setComment(""); }} />
      <span className="mx-1 h-5 w-px bg-gray-200 dark:bg-slate-700" />
      <Tool label="翻译" icon={Languages} onClick={onTranslate} />
    </div>
    {mode && <div className="mt-1.5 flex items-center gap-1 border-t border-gray-100 pt-1.5 dark:border-slate-700">
      <span className="mr-1 text-[10px] text-gray-400">{mode === "highlight" ? "高亮颜色" : "线条"}</span>
      {mode === "underline" && <select aria-label="下划线形状" className="h-6 rounded border border-gray-200 bg-white px-1 text-[10px] dark:border-slate-700 dark:bg-slate-800" value={lineStyle} onChange={(event) => setLineStyle(event.target.value as AnnotationLineStyle)}><option value="solid">实线</option><option value="dashed">虚线</option><option value="dotted">点线</option><option value="double">双线</option><option value="wavy">波浪线</option></select>}
      {COLORS.map((color) => <button key={color.value} type="button" aria-label={`${color.label}${mode === "highlight" ? "高亮" : "下划线"}`} title={color.label} className="h-5 w-5 rounded-full border-2 border-white shadow ring-1 ring-gray-200" style={{ backgroundColor: color.css }} onClick={() => onCreate(mode, color.value, mode === "underline" ? lineStyle : undefined)} />)}
    </div>}
    {commenting && <div className="mt-1.5 w-72 border-t border-gray-100 pt-2 dark:border-slate-700">
      <textarea autoFocus value={comment} onChange={(event) => setComment(event.target.value)} className="input min-h-20 resize-y text-xs" maxLength={5000} placeholder="输入评论…" aria-label="评论内容" />
      <div className="mt-2 flex items-center justify-between"><span className="text-[10px] text-gray-400">{comment.length}/5000</span><div className="flex gap-2"><button type="button" className="text-xs text-gray-500" onClick={() => { setCommenting(false); setComment(""); }}>取消</button><button type="button" className="btn-primary h-7 px-3 text-xs" disabled={!comment.trim()} onClick={() => onCreate("comment", "yellow", undefined, comment.trim())}>保存评论</button></div></div>
    </div>}
  </div>;
}

function Tool({ label, icon: Icon, onClick, active = false }: { label: string; icon: typeof Highlighter; onClick: () => void; active?: boolean }) {
  return <button type="button" title={label} aria-label={label} className={`inline-flex h-7 items-center gap-1 rounded px-2 text-xs ${active ? "bg-primary-50 text-primary-700" : "text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-slate-800"}`} onClick={onClick}><Icon className="h-3.5 w-3.5" /><span className="hidden lg:inline">{label}</span></button>;
}
