import { ChevronLeft, ChevronRight, Minus, Pencil, Plus, ScanLine } from "lucide-react";
import { Link } from "react-router-dom";

import type { PaperReadingStatus } from "@/features/paper/types";
import { useReaderStore } from "@/stores/readerStore";

interface ReaderToolbarProps {
  title: string;
  readingStatus: PaperReadingStatus;
  isReadingStatusPending?: boolean;
  onReadingStatusChange: (status: PaperReadingStatus) => void;
  onEditPaper?: () => void;
}

export function ReaderToolbar({
  title,
  readingStatus,
  isReadingStatusPending = false,
  onReadingStatusChange,
  onEditPaper,
}: ReaderToolbarProps) {
  const currentPage = useReaderStore((state) => state.currentPage);
  const totalPages = useReaderStore((state) => state.totalPages);
  const scale = useReaderStore((state) => state.scale);
  const zoomMode = useReaderStore((state) => state.zoomMode);
  const setCurrentPage = useReaderStore((state) => state.setCurrentPage);
  const prevPage = useReaderStore((state) => state.prevPage);
  const nextPage = useReaderStore((state) => state.nextPage);
  const zoomIn = useReaderStore((state) => state.zoomIn);
  const zoomOut = useReaderStore((state) => state.zoomOut);
  const fitWidth = useReaderStore((state) => state.fitWidth);

  const commitPageInput = (value: string) => {
    const requestedPage = Number.parseInt(value, 10);
    setCurrentPage(Number.isFinite(requestedPage) ? requestedPage : currentPage);
  };

  return (
    <header className="flex min-h-14 shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-3 dark:border-slate-700 dark:bg-slate-900">
      <Link
        to="/library"
        className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800"
      >
        <ChevronLeft className="h-4 w-4" />
        <span className="hidden sm:inline">论文库</span>
      </Link>

      <h1 className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900 dark:text-gray-100" title={title}>
        {title}
      </h1>

      <label className="sr-only" htmlFor="reader-reading-status">阅读状态</label>
      <select
        id="reader-reading-status"
        value={readingStatus}
        onChange={(event) => onReadingStatusChange(event.target.value as PaperReadingStatus)}
        disabled={isReadingStatusPending}
        className="h-8 max-w-24 rounded-md border border-gray-200 bg-white px-2 text-xs text-gray-700 outline-none focus:border-primary-400 disabled:cursor-wait disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-gray-200"
        aria-label="阅读状态"
      >
        <option value="unread">未读</option>
        <option value="reading">阅读中</option>
        <option value="finished">已读</option>
        <option value="archived">已归档</option>
      </select>

      {onEditPaper && <button type="button" className="reader-toolbar-button" onClick={onEditPaper} aria-label="编辑论文信息" title="编辑论文信息"><Pencil className="h-4 w-4" /></button>}

      <div className="flex items-center gap-1 rounded-md border border-gray-200 p-0.5 dark:border-slate-700">
        <button type="button" className="reader-toolbar-button" onClick={zoomOut} aria-label="缩小">
          <Minus className="h-4 w-4" />
        </button>
        <span className="min-w-14 text-center text-xs text-gray-600 dark:text-gray-300">
          {zoomMode === "fit-width" ? "适应宽度" : `${Math.round(scale * 100)}%`}
        </span>
        <button type="button" className="reader-toolbar-button" onClick={zoomIn} aria-label="放大">
          <Plus className="h-4 w-4" />
        </button>
        <button type="button" className="reader-toolbar-button" onClick={fitWidth} aria-label="适应宽度" title="适应宽度">
          <ScanLine className="h-4 w-4" />
        </button>
      </div>

      <div className="flex items-center gap-1 rounded-md border border-gray-200 p-0.5 dark:border-slate-700">
        <button
          type="button"
          className="reader-toolbar-button"
          onClick={prevPage}
          disabled={currentPage <= 1}
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <input
          key={currentPage}
          aria-label="当前页码"
          inputMode="numeric"
          defaultValue={currentPage}
          onBlur={(event) => commitPageInput(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") event.currentTarget.blur();
          }}
          className="h-7 w-10 rounded border border-gray-200 bg-white text-center text-xs outline-none focus:border-primary-400 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-100"
        />
        <span className="px-1 text-xs text-gray-500 dark:text-gray-400">/ {totalPages || "-"}</span>
        <button
          type="button"
          className="reader-toolbar-button"
          onClick={nextPage}
          disabled={!totalPages || currentPage >= totalPages}
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
