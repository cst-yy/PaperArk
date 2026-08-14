import { Highlighter, Languages, MessageSquare, PenLine, Sparkles, StickyNote } from "lucide-react";

import type { AnnotationColor, SelectionContext } from "@/features/annotation/types";

interface SelectionToolbarProps {
  selection: SelectionContext;
  onCreate: (type: "highlight" | "underline" | "comment", color: AnnotationColor) => void;
  onTranslate: () => void;
}

export function SelectionToolbar({ selection, onCreate, onTranslate }: SelectionToolbarProps) {
  return (
    <div
      className="fixed z-50 flex -translate-x-1/2 -translate-y-full items-center gap-1 rounded-lg border border-gray-200 bg-white p-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-900"
      style={{ left: selection.toolbarRect.left + selection.toolbarRect.width / 2, top: Math.max(12, selection.toolbarRect.top - 8) }}
      onMouseDown={(event) => event.preventDefault()}
    >
      <ToolbarButton label="高亮" icon={Highlighter} onClick={() => onCreate("highlight", "yellow")} />
      <ToolbarButton label="下划线" icon={PenLine} onClick={() => onCreate("underline", "red")} />
      <ToolbarButton label="评论" icon={MessageSquare} onClick={() => onCreate("comment", "yellow")} />
      <span className="mx-1 h-5 w-px bg-gray-200 dark:bg-slate-700" />
      <ToolbarButton label="翻译" icon={Languages} onClick={onTranslate} />
      <ToolbarButton label="AI 解释（S11）" icon={Sparkles} disabled />
      <ToolbarButton label="加入笔记（S9）" icon={StickyNote} disabled />
    </div>
  );
}

function ToolbarButton({ label, icon: Icon, onClick, disabled }: { label: string; icon: typeof Highlighter; onClick?: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      className="inline-flex h-7 items-center gap-1 rounded px-2 text-xs text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-200 dark:hover:bg-slate-800"
      onClick={onClick}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="hidden lg:inline">{label.replace(/（.*）/, "")}</span>
    </button>
  );
}
